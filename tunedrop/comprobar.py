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

        # El reproductor de «escuchar antes de descargar» (el módulo de sonido de
        # Qt, con su propio ffmpeg). No necesita altavoces: solo se pregunta si
        # sabe abrir audio AAC, que es el que da YouTube.
        from PySide6.QtCore import QCoreApplication

        try:
            from PySide6.QtMultimedia import QMediaFormat
        except ImportError as exc:
            # En Linux suele ser que falta libpulse (la librería de sonido del sistema).
            log(f"reproductor para escuchar: NO ({exc})")
            ok = False
        else:
            _app = QCoreApplication.instance() or QCoreApplication(sys.argv[:1])
            decodificar = QMediaFormat.ConversionMode.Decode
            tiene_aac = QMediaFormat.AudioCodec.AAC in QMediaFormat().supportedAudioCodecs(decodificar)
            log(f"reproductor para escuchar: {'sí' if tiene_aac else 'NO'} (abre audio AAC)")
            ok &= tiene_aac

        # Idioma (tunedrop/idioma.py) y las traducciones del propio Qt, que ponen
        # en español los botones Sí/No. Si faltan, esos botones salen en inglés:
        # se avisa, pero no es un fallo.
        from PySide6.QtCore import QLibraryInfo, QTranslator

        from . import idioma

        guardado = idioma.idioma_guardado()
        log(f"idioma: {idioma.actual()} ({'elegido' if guardado else 'el del sistema'})")
        carpeta = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        hay = QTranslator().load("qtbase_es", carpeta)
        log(f"traducciones de Qt: {'sí' if hay else 'no (los botones Sí/No saldrán en inglés)'} ({carpeta})")

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
                # La letra es un extra: que no la encuentre no es un error.
                if result.lyrics:
                    tipo = "con tiempos" if result.lyrics.synced else "sin tiempos"
                    log(f"Letra: {len(result.lyrics.plain.splitlines())} líneas ({tipo})")
                else:
                    log("Letra: no encontrada (no es un error)")
                if result.album:
                    log(f"Álbum: {result.album.album} ({result.album.year or 'sin año'})")
                else:
                    log("Álbum: no encontrado en MusicBrainz (no es un error)")
    except Exception:
        log(traceback.format_exc())
        ok = False

    log("RESULTADO: " + ("TODO BIEN" if ok else "FALLO"))
    try:
        Path("tunedrop-comprobacion.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    except OSError:
        pass
    return 0 if ok else 1
