#!/usr/bin/env bash
# ============================================================
#  Instalador de tunedrop para Linux en un solo comando.
#
#  Se usa así (copiar y pegar en una terminal):
#      curl -fsSL https://raw.githubusercontent.com/xcvlad/tunedrop/main/instalar/linux.sh | bash
#
#  Qué hace:
#  1. Busca la última versión publicada en GitHub (Releases).
#  2. Descarga el programa ya compilado (no necesitas Python).
#  3. Lo guarda en ~/.local/share/tunedrop, solo para tu usuario (sin sudo).
#  4. Lo añade al menú de aplicaciones y crea el comando «tunedrop».
#
#  Volver a ejecutarlo actualiza a la última versión.
#  Para desinstalar:
#      curl -fsSL https://raw.githubusercontent.com/xcvlad/tunedrop/main/instalar/linux.sh | bash -s -- --desinstalar
# ============================================================
set -euo pipefail

REPO="xcvlad/tunedrop"
DATOS="${XDG_DATA_HOME:-$HOME/.local/share}"
DESTINO="$DATOS/tunedrop"                         # aquí va el programa
MENU="$DATOS/applications/tunedrop.desktop"       # acceso en el menú de aplicaciones
COMANDO="$HOME/.local/bin/tunedrop"               # para abrirlo escribiendo «tunedrop»

fallo() {
    echo
    echo " [X] $1" >&2
    exit 1
}

# --- Desinstalar -----------------------------------------------
# Solo borra lo que este script creó. Tu música no se toca.
if [ "${1:-}" = "--desinstalar" ]; then
    rm -rf "$DESTINO"
    rm -f "$MENU" "$COMANDO"
    echo " tunedrop se ha desinstalado. Tu música sigue en su carpeta."
    exit 0
fi

echo
echo " === Instalando tunedrop ==="
echo

# --- Comprobaciones --------------------------------------------
command -v curl >/dev/null || fallo "Hace falta curl. Instálalo con: sudo apt install curl (o el gestor de tu distribución)."
command -v tar  >/dev/null || fallo "Hace falta tar."
[ "$(uname -m)" = "x86_64" ] || fallo "De momento solo hay versión para PC de 64 bits (x86_64). Tu equipo es $(uname -m).
     Puedes ejecutarlo desde el código: https://github.com/$REPO#para-programadores"

# --- 1. Buscar la última versión --------------------------------
# La página .../releases/latest redirige a la última versión, por ejemplo
# .../releases/tag/v0.1.0. Nos quedamos con el final («v0.1.0»).
# No usamos la API de GitHub porque solo permite 60 consultas por hora
# desde la misma red (en un aula, varios alumnos se quedarían sin instalar).
echo " [1/4] Buscando la última versión ..."
FINAL=$(curl -fsSLI -o /dev/null -w '%{url_effective}' "https://github.com/$REPO/releases/latest") || true
ETIQUETA="${FINAL##*/}"          # todo lo que va después de la última «/»
case "$ETIQUETA" in
    v*) ;;                        # es una versión: seguimos
    *)  fallo "No se encontró ninguna versión publicada en https://github.com/$REPO/releases" ;;
esac
VERSION="${ETIQUETA#v}"          # «v0.1.0» -> «0.1.0»
ARCHIVO="tunedrop-$VERSION-linux-x86_64.tar.gz"
URL="https://github.com/$REPO/releases/download/$ETIQUETA/$ARCHIVO"
echo "       $ARCHIVO"

# --- 2. Descargar y descomprimir --------------------------------
echo " [2/4] Descargando (unos 200 MB) ..."
TEMPORAL=$(mktemp -d)
trap 'rm -rf "$TEMPORAL"' EXIT
curl -fL --progress-bar "$URL" -o "$TEMPORAL/tunedrop.tar.gz"
tar -xzf "$TEMPORAL/tunedrop.tar.gz" -C "$TEMPORAL"
[ -x "$TEMPORAL/tunedrop/tunedrop" ] || fallo "El archivo descargado no tiene el formato esperado."

# --- 3. Instalar (sustituye la versión anterior si la hay) -------
echo " [3/4] Instalando en $DESTINO ..."
rm -rf "$DESTINO"
mkdir -p "$(dirname "$DESTINO")"
mv "$TEMPORAL/tunedrop" "$DESTINO"

# --- 4. Menú de aplicaciones y comando ---------------------------
# Un archivo .desktop es el «acceso directo» de los escritorios de Linux
# (GNOME, KDE, XFCE...). Hace que tunedrop aparezca como cualquier otra app.
echo " [4/4] Añadiendo tunedrop al menú de aplicaciones ..."
mkdir -p "$(dirname "$MENU")" "$(dirname "$COMANDO")"
cat > "$MENU" <<EOF
[Desktop Entry]
Type=Application
Name=tunedrop
Comment=Descarga música en MP3 con título, artista y carátula
Exec="$DESTINO/tunedrop"
Icon=$DESTINO/_internal/tunedrop/assets/icono.png
Terminal=false
Categories=AudioVideo;Audio;
StartupWMClass=tunedrop
EOF
ln -sf "$DESTINO/tunedrop" "$COMANDO"
command -v update-desktop-database >/dev/null && update-desktop-database "$(dirname "$MENU")" 2>/dev/null || true

# --- Librería del sistema que necesita Qt -------------------------
# La ventana usa Qt, que necesita libxcb-cursor. Falta en algunas instalaciones mínimas.
if command -v ldconfig >/dev/null && ! ldconfig -p | grep -q libxcb-cursor; then
    echo
    echo " [!] Falta la librería libxcb-cursor, que la ventana necesita. Instálala con:"
    echo "       Ubuntu/Debian:  sudo apt install libxcb-cursor0"
    echo "       Fedora:         sudo dnf install xcb-util-cursor"
    echo "       Arch:           sudo pacman -S xcb-util-cursor"
fi

echo
echo " === Listo. Abre tunedrop desde el menú de aplicaciones o escribe: tunedrop ==="
echo
