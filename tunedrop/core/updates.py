"""Aviso de versión nueva: mira en GitHub si hay una tunedrop más reciente.

No usa la API de GitHub (solo deja hacer 60 consultas por hora desde la misma
red): pide la página «releases/latest», que redirige a la última versión, por
ejemplo .../releases/tag/v0.4.0, y se queda con el final. Es el mismo truco que
usan los comandos de instalar (instalar/windows.ps1 y linux.sh).

Actualizar tunedrop es volver a ejecutar ese comando de instalar. Según cómo
esté instalada, la app puede hacerlo sola (Windows y Linux con el comando) o
solo puede explicar qué hacer (NixOS, el .zip portable o desde el código).

Si no hay conexión o GitHub no responde, simplemente no hay aviso.
"""

from __future__ import annotations

import os
import re
import sys
import urllib.request
from pathlib import Path

from .. import __version__
from ..idioma import tr

REPO = "xcvlad/tunedrop"
RELEASES = f"https://github.com/{REPO}/releases"
USER_AGENT = f"tunedrop {__version__} (https://github.com/{REPO})"

INSTALAR_WINDOWS = f"https://raw.githubusercontent.com/{REPO}/main/instalar/windows.ps1"
INSTALAR_LINUX = f"https://raw.githubusercontent.com/{REPO}/main/instalar/linux.sh"


def latest_version(timeout: float = 10) -> str | None:
    """La última versión publicada («0.4.0»), o None si no se puede saber."""
    try:
        req = urllib.request.Request(f"{RELEASES}/latest", method="HEAD",
                                     headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            final = resp.geturl()     # la dirección después de seguir la redirección
    except Exception:
        return None
    etiqueta = final.rstrip("/").rsplit("/", 1)[-1]     # «v0.4.0»
    return etiqueta[1:] if re.fullmatch(r"v\d+(\.\d+)*", etiqueta) else None


def _numeros(version: str) -> tuple[int, ...]:
    """«0.10.2» -> (0, 10, 2), para comparar bien: 0.10 es más nueva que 0.9."""
    return tuple(int(n) for n in re.findall(r"\d+", version))


def is_newer(latest: str, current: str = __version__) -> bool:
    return _numeros(latest) > _numeros(current)


def check() -> str | None:
    """Devuelve la versión nueva si la hay; si no (o no hay conexión), None."""
    latest = latest_version()
    return latest if latest and is_newer(latest) else None


def install_kind() -> str:
    """Cómo está instalada esta tunedrop, para saber cómo se actualiza.

    - "windows": con el instalador (comando de PowerShell o setup.exe).
    - "linux": con el comando de Linux (en ~/.local/share/tunedrop).
    - "nix": con Nix (NixOS).
    - "manual": el .zip o .tar.gz descomprimido en otro sitio, o desde el código.
    """
    if "/nix/store/" in str(Path(__file__).resolve()):
        return "nix"
    if not getattr(sys, "frozen", False):
        return "manual"          # desde el código (python -m tunedrop)
    carpeta = Path(sys.executable).resolve().parent
    if sys.platform == "win32":
        instalada = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "tunedrop"
        return "windows" if carpeta == instalada.resolve() else "manual"
    datos = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
    return "linux" if carpeta == (datos / "tunedrop").resolve() else "manual"


def clean_environment() -> dict:
    """Variables de entorno para abrir otro programa desde tunedrop.

    El programa compilado con PyInstaller guarda datos internos en variables de
    entorno, y cualquier programa que abra las hereda. Si ese programa acaba
    abriendo otra tunedrop (el comando de instalar lo hace al terminar), se
    confundiría con ellas. Esta variable le dice que empiece de cero.
    """
    env = dict(os.environ)
    env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    return env


def update_hint(kind: str) -> str:
    """Qué tiene que hacer la persona cuando la app no puede actualizarse sola."""
    if kind == "nix":
        return tr("Actualízala con «nix profile upgrade tunedrop» o, si está en tu configuración, "
                  "con «nix flake update tunedrop» y reconstruyendo el sistema.")
    if getattr(sys, "frozen", False):
        return tr("Descarga la versión nueva desde la página de novedades.")
    return tr("Actualiza el código con «git pull».")
