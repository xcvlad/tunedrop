"""Conversión con ffmpeg al formato final."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .models import AudioFormat
from .runtime import ffmpeg_path

# Normalización EBU R128 a -14 LUFS, el nivel de Spotify y YouTube.
LOUDNORM = "loudnorm=I=-14:TP=-1.5:LRA=11"


class ConversionError(RuntimeError):
    pass


def build_command(src: Path, dst: Path, fmt: AudioFormat, normalize: bool,
                  source_is_aac: bool = True) -> list[str]:
    cmd = [ffmpeg_path(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
           "-vn", "-map_metadata", "-1"]
    if fmt is AudioFormat.M4A:
        if source_is_aac and not normalize:
            cmd += ["-c:a", "copy"]
        else:
            # Normalizar o partir de Opus obliga a recodificar; 256k deja margen sobre la fuente.
            if normalize:
                cmd += ["-af", LOUDNORM]
            cmd += ["-c:a", "aac", "-b:a", "256k"]
        cmd += ["-movflags", "+faststart"]
    else:
        if normalize:
            cmd += ["-af", LOUDNORM]
        cmd += ["-ar", "44100", "-c:a", "libmp3lame"]
        cmd += ["-q:a", "0"] if fmt is AudioFormat.MP3_V0 else ["-b:a", "320k"]
        # Las etiquetas las escribe mutagen en ID3v2.3 después.
        cmd += ["-id3v2_version", "0", "-write_xing", "1"]
    cmd.append(str(dst))
    return cmd


def convert(src: Path, dst: Path, fmt: AudioFormat, normalize: bool = False,
            source_is_aac: bool = True) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    cmd = build_command(src, dst, fmt, normalize, source_is_aac)
    proc = subprocess.run(cmd, capture_output=True,
                          text=True, creationflags=flags)
    if proc.returncode != 0 or not dst.exists():
        raise ConversionError(proc.stderr.strip() or "ffmpeg falló sin mensaje")
    return dst
