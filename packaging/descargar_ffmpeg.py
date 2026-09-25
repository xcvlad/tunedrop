"""Descarga ffmpeg (versión LGPL) para Windows o Linux en la carpeta bin/ del proyecto.

ffmpeg es el programa que convierte el audio a MP3. Usamos las compilaciones
públicas de BtbN (https://github.com/BtbN/FFmpeg-Builds), que se generan de forma
automática desde el código oficial de ffmpeg. Elegimos la variante LGPL porque
permite distribuirla junto a la app y sigue incluyendo el codificador MP3 (LAME).

Uso:  python packaging/descargar_ffmpeg.py
"""

from __future__ import annotations

import platform
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

BASE_URL = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/"
RAIZ = Path(__file__).resolve().parent.parent
BIN = RAIZ / "bin"


def paquete() -> tuple[str, str]:
    """Qué archivo descargar según el sistema: (nombre del paquete, nombre del ejecutable)."""
    maquina = platform.machine().lower()
    if sys.platform == "win32":
        return "ffmpeg-master-latest-win64-lgpl.zip", "ffmpeg.exe"
    if sys.platform.startswith("linux"):
        # x86_64 es un PC normal; aarch64 es ARM (Raspberry Pi 4/5, algunos portátiles).
        arq = "linuxarm64" if maquina in ("aarch64", "arm64") else "linux64"
        return f"ffmpeg-master-latest-{arq}-lgpl.tar.xz", "ffmpeg"
    sys.exit("No hay descarga automática de ffmpeg para este sistema. "
             "Instálalo con tu gestor de paquetes (en macOS: brew install ffmpeg).")


def _extraer(archivo: Path, ffmpeg: Path, licencia: Path) -> None:
    """Saca del paquete solo el ejecutable y su licencia."""
    def guardar(src, dst: Path) -> None:
        with open(dst, "wb") as out:
            shutil.copyfileobj(src, out)

    if archivo.suffix == ".zip":
        with zipfile.ZipFile(archivo) as z:
            for nombre in z.namelist():
                if nombre.endswith(f"/bin/{ffmpeg.name}"):
                    guardar(z.open(nombre), ffmpeg)
                elif nombre.endswith("/LICENSE.txt"):
                    guardar(z.open(nombre), licencia)
    else:
        with tarfile.open(archivo) as t:
            for miembro in t.getmembers():
                if miembro.isfile() and miembro.name.endswith(f"/bin/{ffmpeg.name}"):
                    guardar(t.extractfile(miembro), ffmpeg)
                elif miembro.isfile() and miembro.name.endswith("/LICENSE.txt"):
                    guardar(t.extractfile(miembro), licencia)


def descargar(destino: Path = BIN) -> Path:
    nombre, exe = paquete()
    ffmpeg = destino / exe
    if ffmpeg.exists():
        print(f"ffmpeg ya está en {ffmpeg.relative_to(RAIZ)}")
        return ffmpeg

    destino.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        archivo = Path(tmp) / nombre
        print("Descargando ffmpeg (entre 50 y 170 MB, puede tardar unos minutos)...")
        with urllib.request.urlopen(BASE_URL + nombre) as resp, open(archivo, "wb") as out:
            total = int(resp.headers.get("Content-Length", 0))
            hecho = 0
            while bloque := resp.read(1 << 20):
                out.write(bloque)
                hecho += len(bloque)
                if total:
                    print(f"\r  {hecho * 100 // total:3d} %", end="", flush=True)
        print()
        _extraer(archivo, ffmpeg, destino / "ffmpeg-LICENSE.txt")

    if not ffmpeg.exists():
        sys.exit(f"No se encontró {exe} dentro del paquete descargado.")
    ffmpeg.chmod(0o755)  # en Linux, sin permiso de ejecución no se puede usar
    print(f"Listo: {ffmpeg.relative_to(RAIZ)}")
    return ffmpeg


if __name__ == "__main__":
    descargar()
