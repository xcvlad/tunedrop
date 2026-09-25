"""Crea el programa de tunedrop para Windows o Linux, listo para distribuir.

Pasos (cada uno está en su propia función, en orden):
  1. Descarga ffmpeg (LGPL) en bin/ si no está.
  2. Copia Deno desde la librería `deno` instalada con pip.
  3. PyInstaller empaqueta Python + librerías + tunedrop en dist/tunedrop/.
  4. Comprime esa carpeta: .zip portable en Windows, .tar.gz en Linux.
  5. Solo en Windows: si tienes Inno Setup, crea también un instalador setup.exe.
  6. Calcula las huellas SHA-256 para que cualquiera pueda verificar las descargas.

Cada sistema compila su propia versión: el .exe se crea en Windows y la de
Linux en Linux (PyInstaller no compila de un sistema para otro).

Uso:  python packaging/build.py
Es exactamente lo mismo que ejecuta GitHub Actions (.github/workflows/release.yml).
"""

from __future__ import annotations

import hashlib
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PACKAGING = RAIZ / "packaging"
BIN = RAIZ / "bin"
DIST = RAIZ / "dist"
BUILD = RAIZ / "build"
WINDOWS = sys.platform == "win32"
EXT = ".exe" if WINDOWS else ""  # en Linux los ejecutables no llevan extensión

sys.path.insert(0, str(PACKAGING))
from descargar_ffmpeg import descargar as descargar_ffmpeg  # noqa: E402


def version() -> str:
    texto = (RAIZ / "tunedrop" / "__init__.py").read_text(encoding="utf-8")
    return re.search(r'__version__ = "([^"]+)"', texto).group(1)


def paso(msg: str) -> None:
    print(f"\n=== {msg} ===", flush=True)


def preparar_binarios() -> None:
    paso("1-2. Preparando ffmpeg y Deno en bin/")
    descargar_ffmpeg(BIN)
    deno_dst = BIN / f"deno{EXT}"
    if not deno_dst.exists():
        import deno

        shutil.copy2(deno.find_deno_bin(), deno_dst)
        print(f"Copiado {deno_dst.relative_to(RAIZ)}")


def pyinstaller() -> Path:
    paso("3. Empaquetando con PyInstaller")
    sep = os.pathsep  # PyInstaller usa "origen;destino" en Windows y "origen:destino" en Linux
    args = [
        str(PACKAGING / "lanzador.py"),
        "--name", "tunedrop",
        "--windowed",                     # sin ventana negra de consola (en Linux no cambia nada)
        "--onedir",                       # carpeta con el .exe: arranca rápido y da menos falsos positivos de antivirus
        "--icon", str(PACKAGING / "icono.ico"),  # Linux lo ignora: allí el icono lo pone el .desktop
        # Pantalla de carga: el lanzador la muestra nada más hacer clic, antes de
        # cargar Python (lo que más tarda). La cierra tunedrop/__main__.py.
        "--splash", str(PACKAGING / "pantalla-carga.png"),
        "--add-data", f"{RAIZ / 'tunedrop' / 'assets'}{sep}tunedrop/assets",
        "--add-binary", f"{BIN / f'ffmpeg{EXT}'}{sep}bin",
        "--add-binary", f"{BIN / f'deno{EXT}'}{sep}bin",
        "--add-data", f"{RAIZ / 'LICENSE'}{sep}licencias",
        "--add-data", f"{BIN / 'ffmpeg-LICENSE.txt'}{sep}licencias",
        "--exclude-module", "tkinter",
        "--exclude-module", "pytest",
        "--distpath", str(DIST),
        "--workpath", str(BUILD / "pyinstaller"),
        "--specpath", str(BUILD),
        "--noconfirm", "--clean",
    ]
    subprocess.run([sys.executable, "-m", "PyInstaller", *args], check=True, cwd=RAIZ)
    app_dir = DIST / "tunedrop"
    print(f"App creada en {app_dir.relative_to(RAIZ)}")
    return app_dir


def comprimir(app_dir: Path, ver: str) -> Path:
    if WINDOWS:
        paso("4. Creando el .zip portable")
        base, formato = DIST / f"tunedrop-{ver}-portable", "zip"
    else:
        # .tar.gz conserva los permisos de ejecución, que en Linux son necesarios.
        paso("4. Creando el .tar.gz para Linux")
        base, formato = DIST / f"tunedrop-{ver}-linux-{platform.machine().lower()}", "gztar"
    archivo = shutil.make_archive(str(base), formato, root_dir=DIST, base_dir=app_dir.name)
    print(f"Creado {Path(archivo).name}")
    return Path(archivo)


def buscar_iscc() -> str | None:
    candidatos = [
        shutil.which("iscc"),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"),
    ]
    return next((c for c in candidatos if c and Path(c).exists()), None)


def instalador(ver: str) -> Path | None:
    paso("5. Creando el instalador con Inno Setup")
    iscc = buscar_iscc()
    if not iscc:
        print("Inno Setup no está instalado: se omite el instalador (el .zip portable ya sirve).")
        print("Para crearlo:  winget install -e --id JRSoftware.InnoSetup")
        return None
    subprocess.run([iscc, f"/DMyAppVersion={ver}", str(PACKAGING / "instalador.iss")],
                   check=True, cwd=RAIZ)
    setup = DIST / f"tunedrop-{ver}-setup.exe"
    print(f"Creado {setup.name}")
    return setup


def huellas(archivos: list[Path]) -> None:
    paso("6. Calculando huellas SHA-256")
    lineas = []
    for f in archivos:
        h = hashlib.sha256(f.read_bytes()).hexdigest()
        lineas.append(f"{h}  {f.name}")
        print(lineas[-1])
    (DIST / "SHA256SUMS.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def main() -> None:
    if not (WINDOWS or sys.platform.startswith("linux")):
        sys.exit("Este script solo sabe crear la versión de Windows o de Linux.")
    ver = version()
    print(f"Compilando tunedrop {ver} para {'Windows' if WINDOWS else 'Linux'}")
    preparar_binarios()
    app_dir = pyinstaller()
    artefactos = [comprimir(app_dir, ver)]
    if WINDOWS:
        setup = instalador(ver)
        if setup:
            artefactos.append(setup)
    huellas(artefactos)
    print("\nTodo listo en la carpeta dist/")


if __name__ == "__main__":
    main()
