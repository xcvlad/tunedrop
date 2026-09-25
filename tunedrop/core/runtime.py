"""Localiza las herramientas externas (ffmpeg, Deno) y arma las opciones base de yt-dlp."""

from __future__ import annotations

import os
import shutil
import sys
from functools import lru_cache
from pathlib import Path


class MissingToolError(RuntimeError):
    pass


def _bin_dirs() -> list[Path]:
    """Carpetas `bin/` donde buscar ffmpeg y Deno antes que en el PATH del sistema."""
    dirs = []
    base = getattr(sys, "_MEIPASS", None)
    if base:  # dentro del .exe creado con PyInstaller
        dirs.append(Path(base) / "bin")
    dirs.append(Path(__file__).resolve().parents[2] / "bin")  # bin/ del proyecto
    return dirs


def _find_in_bins(name: str) -> str | None:
    exe = f"{name}.exe" if os.name == "nt" else name
    for folder in _bin_dirs():
        if (folder / exe).exists():
            return str(folder / exe)
    return None


@lru_cache(maxsize=1)
def ffmpeg_path() -> str:
    found = _find_in_bins("ffmpeg") or shutil.which("ffmpeg")
    if not found:
        if sys.platform == "win32":
            ayuda = "Ejecuta 1_instalar.bat (lo descarga solo) o instálalo con `winget install Gyan.FFmpeg`"
        else:
            ayuda = "Ejecuta 1_instalar.sh (lo descarga solo) o instálalo con `sudo apt install ffmpeg`"
        raise MissingToolError(f"No se encontró ffmpeg. {ayuda} y vuelve a abrir tunedrop.")
    return found


@lru_cache(maxsize=1)
def deno_path() -> str | None:
    """Deno ejecuta el JavaScript de YouTube que yt-dlp necesita para descifrar los streams."""
    bundled = _find_in_bins("deno")
    if bundled:
        return bundled
    try:
        import deno

        return deno.find_deno_bin()
    except Exception:
        return shutil.which("deno")


def base_ydl_options() -> dict:
    opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "socket_timeout": 20,
        "retries": 5,
        "fragment_retries": 5,
    }
    deno = deno_path()
    if deno:
        opts["js_runtimes"] = {"deno": {"path": deno}}
    return opts
