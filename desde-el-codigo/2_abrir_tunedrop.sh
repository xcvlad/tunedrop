#!/usr/bin/env bash
# ============================================================
#  PASO 2 (Linux): abre tunedrop.
#  Es el equivalente de 2_abrir_tunedrop.bat. Se ejecuta con:
#      bash desde-el-codigo/2_abrir_tunedrop.sh
#  Si algo falla, el error aparece en esta terminal.
# ============================================================
cd "$(dirname "$0")/.."     # el script vive en desde-el-codigo/, pero trabaja en la carpeta del proyecto

if [ ! -x .venv/bin/python ]; then
    echo " Primero tienes que ejecutar: bash desde-el-codigo/1_instalar.sh"
    exit 1
fi

exec .venv/bin/python -m tunedrop "$@"
