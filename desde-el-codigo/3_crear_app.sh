#!/usr/bin/env bash
# ============================================================
#  PASO 3 (Linux, opcional): crea el programa para distribuir.
#  Es el equivalente de 3_crear_exe.bat. Se ejecuta con:
#      bash desde-el-codigo/3_crear_app.sh
#  Resultado en la carpeta dist/ :
#   - tunedrop/                          (la app: se abre con dist/tunedrop/tunedrop)
#   - tunedrop-X.Y.Z-linux-x86_64.tar.gz (esa carpeta comprimida)
#  Todo el proceso esta en packaging/build.py
# ============================================================
set -e
cd "$(dirname "$0")/.."     # el script vive en desde-el-codigo/, pero trabaja en la carpeta del proyecto

if [ ! -x .venv/bin/python ]; then
    echo " Primero tienes que ejecutar: bash desde-el-codigo/1_instalar.sh"
    exit 1
fi

.venv/bin/python -m pip install -r requirements-dev.txt --quiet
.venv/bin/python packaging/build.py

echo
echo " === Hecho. Mira la carpeta dist/ ==="
