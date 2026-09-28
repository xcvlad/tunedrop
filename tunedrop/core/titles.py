"""Limpieza de títulos de vídeo para convertirlos en artista y título de canción."""

from __future__ import annotations

import re

# Palabras de relleno de los títulos de vídeos musicales. Un paréntesis (o una
# coletilla del final, tras « - » o « | ») se quita si TODAS sus palabras son de
# esta lista o años. Así se quitan también las mezclas, como
# «(Official Video Remastered)» u «(Official 4K Video)», pero se conservan los
# que dicen algo de la canción: «(feat. Rosalía)», «(Live)», «(Remix)»,
# «(with Justin Bieber)»... porque tienen palabras que no son de relleno.
_PALABRAS_RELLENO = {
    # «oficial» en varios idiomas
    "official", "oficial", "officiel", "officielle", "ufficiale", "offizielles",
    # vídeo / audio
    "music", "musical", "musica", "música", "video", "vídeo", "videoclip", "clip",
    "audio", "mv", "visualizer", "visualiser", "visualizador",
    # letras
    "lyric", "lyrics", "letra", "letras", "con", "with",
    # calidad de imagen
    "hd", "hq", "uhd", "4k", "8k", "1080p", "720p", "60fps",
    # remasterizaciones
    "remaster", "remastered", "remasterizado", "remasterizada", "remasterización",
    "full", "version", "versión", "fps", "studio", "estudio", "upgrade", "upgraded",
    # artículos y enlaces: «(La Letra / Lyrics)», «(Video de la canción)»...
    "la", "el", "the", "de", "del",
    # otros
    "explicit",
}

# Un grupo entre paréntesis, corchetes, llaves o 【corchetes japoneses】.
_GRUPO = re.compile(r"\s*[(\[{【]([^()\[\]{}【】]*)[)\]}】]")
# La última parte tras « - », « – », « | » o « // »: «Canción - Official Video».
_PARTE_FINAL = re.compile(r"\s+(?:-|–|—|\||//)\s+([^-–—|/]*)$")

# «HD», «HQ» o «4K» sueltos al final, sin paréntesis: «Canción HQ».
_CALIDAD_FINAL = re.compile(r"\s+(hd|hq|4k)$", re.IGNORECASE)

# «Artista 'Canción' Official MV»: el formato de los vídeos de K-pop. La comilla
# de apertura va tras un espacio, así no confunde «Guns N' Roses» ni «Bunny's».
_CITADO = re.compile(r"^(.+?)\s+['‘\"“](.+?)['’\"”]")

_TOPIC = re.compile(r"\s*-\s*Topic$", re.IGNORECASE)
_VEVO = re.compile(r"VEVO$", re.IGNORECASE)
_SEPARATORS = (" - ", " – ", " — ", " || ", " | ")


def _es_relleno(texto: str) -> bool:
    """True si todas las palabras del texto son de relleno o números (años, «60 fps»...)."""
    palabras = re.findall(r"[\w']+", texto.lower().replace("m/v", "mv"))
    return bool(palabras) and all(p in _PALABRAS_RELLENO or p.isdigit() for p in palabras)


def clean_title(title: str) -> str:
    # 1. Quita los paréntesis de relleno, estén donde estén.
    cleaned = _GRUPO.sub(lambda m: "" if _es_relleno(m.group(1)) else m.group(0), title)
    # 2. Quita las coletillas de relleno del final, una a una
    #    («Canción - Remastered 2011 - Official Video»).
    while (final := _PARTE_FINAL.search(cleaned)) and _es_relleno(final.group(1)):
        cleaned = cleaned[:final.start()]
    cleaned = _CALIDAD_FINAL.sub("", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip(" -–—|")


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
            # «@coldplay» -> «coldplay»: la @ es de las menciones de YouTube.
            artist = artist.strip().lstrip("@")
            # «Canción | Nombre del álbum»: lo que va tras « | » suele ser el álbum.
            song = song.split(" | ")[0]
            if artist and song.strip():
                return artist, clean_title(song)
    if citado := _CITADO.match(cleaned):
        return citado.group(1).strip(), citado.group(2).strip()
    return (clean_channel(channel) or "Desconocido"), cleaned
