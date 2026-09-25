"""Nombres de archivo seguros para FAT32 (el sistema de archivos de la mayoría de reproductores e iPods)."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

_INVALID = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
MAX_COMPONENT = 100  # por debajo de los 255 de FAT32 para dejar margen a la ruta completa

def sanitize(name: str, fallback: str = "Sin título") -> str:
    name = unicodedata.normalize("NFC", name or "")
    name = _INVALID.sub("_", name)
    name = re.sub(r"\s+", " ", name).strip().rstrip(". ")
    if name.upper().split(".")[0] in _RESERVED:
        name = f"_{name}"
    if len(name) > MAX_COMPONENT:
        name = name[:MAX_COMPONENT].rstrip(". ")
    return name or fallback


def build_output_path(root: Path, *, artist: str, title: str, extension: str) -> Path:
    """Ruta final de la canción: todas sueltas en la carpeta de música, sin subcarpetas.

    Formato: «Artista - Título.mp3». Así se ordenan por artista en cualquier explorador
    o reproductor, y el álbum y el número de pista van dentro del archivo, en las etiquetas.
    """
    name = sanitize(f"{sanitize(artist, 'Desconocido')} - {sanitize(title)}")
    return root / f"{name}.{extension}"


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for i in range(2, 1000):
        candidate = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not candidate.exists():
            return candidate
    raise FileExistsError(path)
