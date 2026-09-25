"""Búsqueda de canciones y resolución de enlaces (vídeos, playlists, álbumes, SoundCloud, Bandcamp…)."""

from __future__ import annotations

import re

from .models import Track
from .runtime import base_ydl_options

_URL = re.compile(r"^(https?://|www\.)\S+$", re.IGNORECASE)
_YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


class SearchError(RuntimeError):
    pass


def is_url(text: str) -> bool:
    return bool(_URL.match(text.strip()))


def search(query: str, limit: int = 20) -> list[Track]:
    """Busca en YouTube directamente, sin pasar por ninguna API ni servidor de terceros."""
    query = query.strip()
    if not query:
        return []
    return _extract(f"ytsearch{limit}:{query}")


def resolve(url: str) -> list[Track]:
    """Convierte un enlace en canciones: uno para un vídeo y varios para una playlist o un álbum."""
    url = url.strip()
    if url.startswith("www."):
        url = "https://" + url
    return _extract(url)


def _extract(target: str) -> list[Track]:
    # yt-dlp se importa aquí y no arriba: tarda en cargarse y así la ventana
    # de la app aparece antes (ver ui/startup.py).
    import yt_dlp

    opts = {**base_ydl_options(), "extract_flat": "in_playlist", "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(target, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise SearchError(_friendly(str(exc))) from exc
    if not info:
        return []
    entries = info.get("entries")
    if entries is None:
        return [entry_to_track(info)]
    tracks = [entry_to_track(e) for e in entries if e and e.get("id")]
    # Los vídeos privados o borrados de una playlist aparecen sin duración y con un título fijo.
    return [t for t in tracks if t.title not in ("[Private video]", "[Deleted video]")]


def entry_to_track(entry: dict) -> Track:
    video_id = str(entry.get("id"))
    extractor = (entry.get("ie_key") or entry.get("extractor_key") or "youtube").lower()
    url = entry.get("webpage_url") or entry.get("url") or ""
    if extractor.startswith("youtube") and _YT_ID.match(video_id):
        url = f"https://www.youtube.com/watch?v={video_id}"
    artists = entry.get("artists")
    return Track(
        id=video_id,
        url=url,
        title=entry.get("track") or entry.get("title") or video_id,
        channel=entry.get("channel") or entry.get("uploader") or "",
        duration=int(entry["duration"]) if entry.get("duration") else None,
        thumbnail=_pick_thumbnail(entry, video_id, extractor),
        source="youtube" if extractor.startswith("youtube") else extractor,
        artist=", ".join(artists) if artists else entry.get("artist"),
        album=entry.get("album"),
    )


def _pick_thumbnail(entry: dict, video_id: str, extractor: str) -> str | None:
    thumbs = [t for t in entry.get("thumbnails") or [] if t.get("url")]
    # Basta una miniatura mediana para la tarjeta; la carátula grande se baja al descargar.
    sized = [t for t in thumbs if (t.get("width") or 0) and t["width"] <= 480]
    if sized:
        return max(sized, key=lambda t: t["width"])["url"]
    if thumbs:
        return thumbs[-1]["url"]
    if entry.get("thumbnail"):
        return entry["thumbnail"]
    if extractor.startswith("youtube") and _YT_ID.match(video_id):
        return f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg"
    return None


def _friendly(message: str) -> str:
    message = message.replace("ERROR: ", "")
    if "Unsupported URL" in message:
        return "Ese enlace no es compatible."
    if "Private video" in message:
        return "Ese vídeo es privado."
    if "Video unavailable" in message:
        return "Ese vídeo no está disponible."
    return message
