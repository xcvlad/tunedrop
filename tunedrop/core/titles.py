"""Limpieza de títulos de vídeo para convertirlos en artista y título de canción."""

from __future__ import annotations

import re

# Coletillas típicas de los vídeos musicales que sobran en una etiqueta de canción.
_NOISE = re.compile(
    r"""\s*[\(\[\{]\s*(
        official\s*(music\s*)?(video|audio|lyric\s*video|visualizer)?
        | (video|audio)\s*oficial | v[íi]deo\s*oficial | videoclip(\s*oficial)?
        | lyrics? | letra | lyric\s*video | con\s*letra
        | hd | hq | 4k | 1080p | 720p | remaster(ed)?\s*(\d{4})?
        | audio | visuali[sz]er | clip\s*officiel | explicit
        )\s*[\)\]\}]""",
    re.IGNORECASE | re.VERBOSE,
)
_TRAILING_NOISE = re.compile(
    r"\s*[-|–]\s*(official\s*(music\s*)?(video|audio)|lyrics?|letra|v[íi]deo\s*oficial)\s*$",
    re.IGNORECASE,
)
_TOPIC = re.compile(r"\s*-\s*Topic$", re.IGNORECASE)
_VEVO = re.compile(r"VEVO$", re.IGNORECASE)
_SEPARATORS = (" - ", " – ", " — ", " | ")


def clean_title(title: str) -> str:
    cleaned = _NOISE.sub("", title)
    cleaned = _TRAILING_NOISE.sub("", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip(" -–|")


def clean_channel(channel: str) -> str:
    channel = _TOPIC.sub("", channel or "")
    # "ArtistVEVO" -> "Artist"; no toca nombres que simplemente contienen "vevo".
    if _VEVO.search(channel) and len(channel) > 4:
        channel = _VEVO.sub("", channel)
    return channel.strip()


def split_artist_title(title: str, channel: str = "") -> tuple[str, str]:
    """Devuelve (artista, título) a partir del título del vídeo y el canal."""
    cleaned = clean_title(title)
    for sep in _SEPARATORS:
        if sep in cleaned:
            artist, song = cleaned.split(sep, 1)
            if artist.strip() and song.strip():
                return artist.strip(), clean_title(song)
    return (clean_channel(channel) or "Desconocido"), cleaned
