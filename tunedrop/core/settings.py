"""Configuración del usuario, guardada como JSON en su carpeta de datos."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from .. import APP_NAME
from .models import AudioFormat


def data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    path = base / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def _linux_music_dir() -> Path | None:
    """Carpeta de música del escritorio de Linux, que puede estar traducida (p. ej. ~/Música).

    La define ~/.config/user-dirs.dirs con una línea como: XDG_MUSIC_DIR="$HOME/Música"
    """
    config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "user-dirs.dirs"
    try:
        for linea in config.read_text(encoding="utf-8").splitlines():
            if linea.startswith("XDG_MUSIC_DIR="):
                valor = linea.split("=", 1)[1].strip().strip('"')
                ruta = Path(valor.replace("$HOME", str(Path.home())))
                # Si apunta a la carpeta personal, es que no hay carpeta de música.
                return ruta if ruta != Path.home() else None
    except OSError:
        pass
    return None


def default_music_dir() -> Path:
    music = None
    if sys.platform.startswith("linux"):
        music = _linux_music_dir()
    return (music or Path.home() / "Music") / APP_NAME


@dataclass
class Settings:
    output_dir: str = str(default_music_dir())
    audio_format: str = AudioFormat.MP3_V0.value
    normalize: bool = False
    concurrent: int = 3
    skip_downloaded: bool = True

    @property
    def format(self) -> AudioFormat:
        try:
            return AudioFormat(self.audio_format)
        except ValueError:
            return AudioFormat.MP3_V0

    @classmethod
    def load(cls, path: Path | None = None) -> Settings:
        path = path or data_dir() / "settings.json"
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in known})

    def save(self, path: Path | None = None) -> None:
        path = path or data_dir() / "settings.json"
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
