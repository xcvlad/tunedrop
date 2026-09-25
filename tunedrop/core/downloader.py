"""Descarga completa de una canción: audio, conversión, etiquetas y carátula, en la carpeta de música."""

from __future__ import annotations

import shutil
import tempfile
import threading
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import yt_dlp

from .converter import convert
from .models import AudioFormat, Track
from .paths import build_output_path, unique_path
from .runtime import base_ydl_options
from .tagger import Tags, fetch_image, prepare_cover, write_tags
from .titles import clean_channel, split_artist_title


class Stage(str, Enum):
    QUEUED = "En cola"
    FETCHING = "Preparando"
    DOWNLOADING = "Descargando"
    CONVERTING = "Convirtiendo"
    TAGGING = "Etiquetando"
    DONE = "Listo"
    SKIPPED = "Ya la tenías"
    FAILED = "Error"
    CANCELLED = "Cancelada"


# (etapa, progreso 0-1, texto extra)
ProgressCallback = Callable[[Stage, float, str], None]


class Cancelled(Exception):
    pass


@dataclass
class DownloadOptions:
    output_dir: Path
    audio_format: AudioFormat
    normalize: bool = False


@dataclass
class DownloadResult:
    path: Path
    source_bitrate: float | None  # kbps reales del audio original
    source_codec: str | None


def audio_selector(fmt: AudioFormat) -> str:
    if fmt is AudioFormat.M4A:
        # AAC original para copiarlo sin pérdidas; si no hay, el mejor audio y se recodifica.
        return "bestaudio[ext=m4a]/bestaudio/best"
    return "bestaudio/best"


def download_track(
    track: Track,
    options: DownloadOptions,
    progress: ProgressCallback,
    cancel_event: threading.Event | None = None,
) -> DownloadResult:
    cancel_event = cancel_event or threading.Event()

    def check_cancel():
        if cancel_event.is_set():
            raise Cancelled()

    def hook(d: dict):
        check_cancel()
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            speed = d.get("speed")
            extra = f"{speed / 1_048_576:.1f} MB/s" if speed else ""
            progress(Stage.DOWNLOADING, done / total if total else 0.0, extra)

    progress(Stage.FETCHING, 0.0, "")
    workdir = Path(tempfile.mkdtemp(prefix="tunedrop-"))
    try:
        ydl_opts = {
            **base_ydl_options(),
            "format": audio_selector(options.audio_format),
            "outtmpl": str(workdir / "audio.%(ext)s"),
            "progress_hooks": [hook],
            "noplaylist": True,
            "writethumbnail": False,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(track.url, download=True)
        except yt_dlp.utils.DownloadError as exc:
            if cancel_event.is_set():
                raise Cancelled() from exc
            raise RuntimeError(str(exc).replace("ERROR: ", "")) from exc
        check_cancel()

        downloaded = next((p for p in workdir.iterdir() if p.stem == "audio"), None)
        if not downloaded:
            raise RuntimeError("yt-dlp no produjo ningún archivo de audio")

        tags = build_tags(info, track)
        target = unique_path(build_output_path(
            options.output_dir,
            artist=tags.album_artist or tags.artist, title=tags.title,
            extension=options.audio_format.extension,
        ))

        fmt = options.audio_format
        progress(Stage.CONVERTING, 1.0, "")
        temp_out = workdir / f"out.{fmt.extension}"
        convert(downloaded, temp_out, fmt, options.normalize,
                source_is_aac=str(info.get("acodec", "")).startswith("mp4a"))
        check_cancel()

        progress(Stage.TAGGING, 1.0, "")
        cover = _best_cover(info)
        write_tags(temp_out, tags, cover)

        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(temp_out), target)
        progress(Stage.DONE, 1.0, "")
        return DownloadResult(target, info.get("abr"), info.get("acodec"))
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def build_tags(info: dict, track: Track) -> Tags:
    """Prefiere los metadatos musicales de YouTube Music; si no hay, los saca del título."""
    artists = info.get("artists") or ([info["artist"]] if info.get("artist") else None)
    song = info.get("track")
    if artists and song:
        artist = ", ".join(dict.fromkeys(artists))
        title = song
    else:
        artist, title = split_artist_title(info.get("title") or track.title,
                                           info.get("channel") or track.channel)
    album_artist = info.get("album_artist") or (artists[0] if artists else artist)
    year = info.get("release_year") or info.get("release_date") or info.get("upload_date")
    return Tags(
        title=title.strip(),
        artist=artist.strip(),
        album=info.get("album") or None,
        album_artist=clean_channel(album_artist) or artist,
        track_number=info.get("track_number"),
        year=str(year)[:4] if year else None,
        comment=info.get("webpage_url") or track.url,
    )


def _best_cover(info: dict) -> bytes | None:
    thumbs = [t for t in info.get("thumbnails") or [] if t.get("url")]
    # yt-dlp las ordena de peor a mejor según su preferencia.
    thumbs.sort(key=lambda t: (t.get("preference") or 0, t.get("width") or 0))
    for thumb in reversed(thumbs[-4:]):
        url = thumb["url"]
        if url.endswith(".webp") and "i.ytimg.com" in url:
            url = url.replace("/vi_webp/", "/vi/").replace(".webp", ".jpg")
        data = fetch_image(url)
        if data:
            try:
                return prepare_cover(data)
            except Exception:
                continue
    return None

