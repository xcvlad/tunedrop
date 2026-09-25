"""Autodiagnóstico sin interfaz:  tunedrop.exe --comprobar [enlace]

Comprueba que ffmpeg, Deno y yt-dlp funcionan. Si se pasa un enlace, además
descarga esa canción a una carpeta temporal y verifica el MP3 resultante.
El resultado se guarda en tunedrop-comprobacion.txt (el .exe no tiene consola)
y el código de salida es 0 si todo va bien.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import traceback
from pathlib import Path


def ejecutar(args: list[str]) -> int:
    lineas: list[str] = []

    def log(msg: str) -> None:
        lineas.append(msg)
        if sys.stdout:
            print(msg, flush=True)

    ok = True
    try:
        import yt_dlp

        from .core.runtime import deno_path, ffmpeg_path

        log(f"yt-dlp {yt_dlp.version.__version__}")
        ff = ffmpeg_path()
        out = subprocess.run([ff, "-hide_banner", "-encoders"], capture_output=True, text=True)
        tiene_mp3 = "libmp3lame" in out.stdout
        log(f"ffmpeg: {ff} (codificador MP3: {'sí' if tiene_mp3 else 'NO'})")
        ok &= tiene_mp3
        deno = deno_path()
        if deno:
            v = subprocess.run([deno, "--version"], capture_output=True, text=True).stdout.split("\n")[0]
            log(f"deno: {deno} ({v})")
        else:
            log("deno: NO encontrado")
            ok = False

        if args:
            from .core.downloader import DownloadOptions, download_track
            from .core.models import AudioFormat
            from .core.search import resolve

            track = resolve(args[0])[0]
            log(f"Descargando: {track.title}")
            with tempfile.TemporaryDirectory() as tmp:
                result = download_track(
                    track, DownloadOptions(Path(tmp), AudioFormat.MP3_V0),
                    lambda *_: None)
                size = result.path.stat().st_size
                log(f"OK: {result.path.name} ({size / 1e6:.1f} MB, origen {result.source_codec} "
                    f"{result.source_bitrate} kbps)")
    except Exception:
        log(traceback.format_exc())
        ok = False

    log("RESULTADO: " + ("TODO BIEN" if ok else "FALLO"))
    try:
        Path("tunedrop-comprobacion.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    except OSError:
        pass
    return 0 if ok else 1
