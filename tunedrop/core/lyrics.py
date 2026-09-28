"""Letras de las canciones, sacadas de LRCLIB (https://lrclib.net).

LRCLIB es una base de datos de letras gratuita y abierta: no pide registrarse
ni ninguna clave. De cada canción da dos versiones de la letra:

- normal («plainLyrics»): el texto tal cual. Se guarda dentro del MP3/M4A, y
  el iPod la muestra al pulsar el botón central mientras suena.
- sincronizada («syncedLyrics»): cada línea con el momento en que se canta,
  por ejemplo «[00:07.13] Caught in a landslide». Es el formato .lrc, que
  algunos reproductores muestran a la vez que suena la canción.

Una misma canción suele estar varias veces (versión de álbum, directo,
recortada...), cada una con su duración. Se elige la que dura lo mismo que el
audio descargado, para que los tiempos de la sincronizada cuadren.

Si no hay conexión, LRCLIB no responde o no tiene la canción, las funciones
devuelven None: la letra es un extra y nunca debe estropear una descarga.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass

from .. import __version__

API = "https://lrclib.net/api/search"
# LRCLIB pide que cada programa se identifique, para saber quién le consulta.
USER_AGENT = f"tunedrop {__version__} (https://github.com/xcvlad/tunedrop)"

# Si la mejor versión encontrada dura más de esto de diferencia con nuestro
# audio, seguramente es otra versión: el texto sirve, pero los tiempos no.
MARGEN_SEGUNDOS = 10

# «[01:23.45]» al principio de una línea de una letra sincronizada.
_TIEMPO = re.compile(r"^\s*\[\d+:\d+(?:[.:]\d+)?\]\s?", re.MULTILINE)


@dataclass
class Lyrics:
    plain: str                  # la letra normal
    synced: str | None = None   # la sincronizada (.lrc), si la hay y cuadra


def find_lyrics(artist: str, title: str, duration: float | None = None,
                timeout: float = 10) -> Lyrics | None:
    """Busca la letra de una canción. Devuelve None si no la encuentra."""
    # Primero por artista y título por separado (más preciso); si no sale nada,
    # con los dos juntos, que encuentra títulos escritos algo distinto.
    for params in ({"artist_name": artist, "track_name": title}, {"q": f"{artist} {title}"}):
        results = _search(params, timeout)
        lyrics = pick_best(results, duration)
        if lyrics:
            return lyrics
    return None


def _search(params: dict, timeout: float) -> list[dict]:
    url = f"{API}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except Exception:
        return []
    return data if isinstance(data, list) else []


def pick_best(results: list[dict], duration: float | None) -> Lyrics | None:
    """Elige, entre los resultados de LRCLIB, la letra que mejor encaja con el audio."""
    candidates = [r for r in results if r.get("plainLyrics") or r.get("syncedLyrics")]
    if not candidates:
        return None

    def diferencia(r: dict) -> float:
        if not duration or not r.get("duration"):
            return 0.0
        return abs(r["duration"] - duration)

    if duration:
        # Primero las que duran casi lo mismo (±3 s); entre ellas, mejor con
        # sincronizada; y después, la más cercana.
        candidates.sort(key=lambda r: (diferencia(r) > 3, not r.get("syncedLyrics"), diferencia(r)))
    else:
        candidates.sort(key=lambda r: not r.get("syncedLyrics"))
    best = candidates[0]

    synced = (best.get("syncedLyrics") or "").strip() or None
    plain = (best.get("plainLyrics") or "").strip() or strip_timestamps(synced or "")
    if not plain:
        return None
    if duration and diferencia(best) > MARGEN_SEGUNDOS:
        synced = None   # otra versión de la canción: los tiempos no cuadrarían
    return Lyrics(plain=plain, synced=synced)


def strip_timestamps(synced: str) -> str:
    """Quita los tiempos «[mm:ss.xx]» de una letra sincronizada."""
    return _TIEMPO.sub("", synced).strip()
