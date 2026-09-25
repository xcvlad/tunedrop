#!/usr/bin/env bash
# ============================================================
#  PASO 1 (Linux): prepara tunedrop en este ordenador (solo una vez).
#  Es el equivalente de 1_instalar.bat. Se ejecuta con:
#      bash desde-el-codigo/1_instalar.sh
#  - Comprueba que Python 3.10+ esta instalado.
#  - Crea un "entorno virtual" (.venv): una carpeta con las
#    librerias del proyecto, sin tocar el resto del sistema.
#  - Instala las librerias de requirements.txt.
#  - Descarga ffmpeg en bin/ si no lo tienes.
#  - Anade tunedrop al menu de aplicaciones del escritorio.
# ============================================================
set -e                      # si un comando falla, el script se detiene
cd "$(dirname "$0")/.."     # el script vive en desde-el-codigo/, pero trabaja en la carpeta del proyecto

fallo() {
    echo
    echo " [X] $1"
    exit 1
}
trap 'fallo "Algo ha fallado. Lee el mensaje de arriba para ver el motivo."' ERR

echo
echo " === Instalando tunedrop ==="
echo

# --- Python ---------------------------------------------------
if ! command -v python3 >/dev/null; then
    fallo "No se encuentra Python. Instalalo con tu gestor de paquetes:
     Ubuntu/Debian:  sudo apt install python3 python3-venv
     Fedora:         sudo dnf install python3
     Arch:           sudo pacman -S python"
fi
python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" \
    || fallo "Tu Python es demasiado antiguo. Hace falta la version 3.10 o superior."

# --- Entorno virtual -------------------------------------------
# Si .venv existe pero no tiene pip, quedo a medias en un intento anterior: se rehace.
if ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
    echo " [1/4] Creando el entorno virtual .venv ..."
    rm -rf .venv
    # En Ubuntu/Debian el modulo venv va en un paquete aparte.
    if ! python3 -m venv .venv; then
        rm -rf .venv
        fallo "No se pudo crear el entorno virtual. En Ubuntu/Debian: sudo apt install python3-venv"
    fi
else
    echo " [1/4] El entorno virtual .venv ya existe."
fi

echo " [2/4] Instalando librerias (puede tardar un par de minutos) ..."
.venv/bin/python -m pip install --upgrade pip --quiet
.venv/bin/python -m pip install -r requirements.txt --quiet

# --- ffmpeg ----------------------------------------------------
echo " [3/4] Comprobando ffmpeg ..."
if command -v ffmpeg >/dev/null; then
    echo "       ffmpeg ya esta instalado en el sistema."
else
    .venv/bin/python packaging/descargar_ffmpeg.py
fi

# --- Acceso en el menu de aplicaciones -------------------------
# Un archivo .desktop es el "acceso directo" de los escritorios de Linux
# (GNOME, KDE, XFCE...). Se guarda solo para tu usuario, sin sudo.
echo " [4/4] Anadiendo tunedrop al menu de aplicaciones ..."
CARPETA="$(pwd)"
MENU="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$MENU"
cat > "$MENU/tunedrop.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=tunedrop
Comment=Descarga musica en MP3 con titulo, artista y caratula
Exec="$CARPETA/.venv/bin/python" -m tunedrop
Path=$CARPETA
Icon=$CARPETA/tunedrop/assets/icono.png
Terminal=false
Categories=AudioVideo;Audio;
StartupWMClass=tunedrop
EOF

# --- Librerias del sistema que necesita Qt ----------------------
# PySide6 (Qt) usa algunas librerias graficas del sistema. La que suele
# faltar en instalaciones minimas es libxcb-cursor.
if command -v ldconfig >/dev/null && ! ldconfig -p | grep -q libxcb-cursor; then
    echo
    echo " [!] Falta la libreria libxcb-cursor, que la ventana de Qt necesita."
    echo "     Instalala antes de abrir la app:"
    echo "       Ubuntu/Debian:  sudo apt install libxcb-cursor0"
    echo "       Fedora:         sudo dnf install xcb-util-cursor"
    echo "       Arch:           sudo pacman -S xcb-util-cursor"
fi

echo
echo " === Todo listo. Abre tunedrop desde el menu de aplicaciones o con: bash desde-el-codigo/2_abrir_tunedrop.sh ==="
echo
