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
#  En NixOS no instala nada: explica cómo hacerlo con Nix (flake.nix).
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
TEMPORAL=""                                       # carpeta de trabajo (se crea más abajo)

# ============================================================
#  Aspecto: colores, símbolos y dibujos de la terminal
# ============================================================

# Colores y animaciones solo si la salida es una terminal de verdad (no un
# archivo) y el usuario no los ha desactivado con la variable NO_COLOR.
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ] && [ "${TERM:-dumb}" != "dumb" ]; then
    BONITO=1
else
    BONITO=0
fi

# Los dibujos usan caracteres especiales (█ ✔ ━). Si la terminal no usa
# UTF-8, no los sabría mostrar, así que usamos letras normales.
case "${LC_ALL:-${LC_CTYPE:-${LANG:-}}}" in
    *[Uu][Tt][Ff]-8* | *[Uu][Tt][Ff]8*) UNICODE=1 ;;
    *) UNICODE=0 ;;
esac

if [ "$BONITO" = 1 ]; then
    # Códigos ANSI: secuencias que la terminal entiende como «cambia de color».
    # 38;5;N elige el color N de una paleta de 256. Son los colores de la app.
    NORMAL=$'\033[0m'
    NEGRITA=$'\033[1m'
    TENUE=$'\033[2m'
    VIOLETA=$'\033[38;5;135m'
    VERDE=$'\033[38;5;79m'
    ROJO=$'\033[38;5;204m'
    AMARILLO=$'\033[38;5;221m'
    GRIS=$'\033[38;5;239m'
    BORRAR_LINEA=$'\r\033[2K'     # vuelve al principio de la línea y la borra
    # Un color para cada letra del logo, del violeta al fucsia (como el icono).
    # Las terminales modernas admiten 16 millones de colores («truecolor»).
    case "${COLORTERM:-}" in
        truecolor | 24bit)
            COLORES=("139;92;246" "150;89;245" "161;86;244" "172;83;243"
                     "184;79;242" "195;76;241" "206;73;240" "217;70;239")
            for i in "${!COLORES[@]}"; do COLORES[i]=$'\033[1;38;2;'"${COLORES[i]}m"; done ;;
        *)
            COLORES=()
            for n in 99 99 135 135 171 171 207 207; do COLORES+=($'\033[1;38;5;'"${n}m"); done ;;
    esac
else
    NORMAL="" NEGRITA="" TENUE="" VIOLETA="" VERDE="" ROJO="" AMARILLO="" GRIS=""
    BORRAR_LINEA=""
    COLORES=("" "" "" "" "" "" "" "")
fi

if [ "$UNICODE" = 1 ]; then
    BIEN="✔" MAL="✘" AVISO="!" NOTA="♪" BARRA="━"
    GIRO=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")    # la «ruedita» que gira
    CAJA=("╭" "╮" "╰" "╯" "─" "│")
else
    BIEN="ok" MAL="x" AVISO="!" NOTA="*" BARRA="#"
    GIRO=("|" "/" "-" "\\")
    CAJA=("+" "+" "+" "+" "-" "|")
fi

# El logo, dibujado con bloques. Cada letra tiene su ancho (en columnas) para
# poder pintarla de un color distinto.
LOGO=(
    "████████╗██╗   ██╗███╗   ██╗███████╗██████╗ ██████╗  ██████╗ ██████╗ "
    "╚══██╔══╝██║   ██║████╗  ██║██╔════╝██╔══██╗██╔══██╗██╔═══██╗██╔══██╗"
    "   ██║   ██║   ██║██╔██╗ ██║█████╗  ██║  ██║██████╔╝██║   ██║██████╔╝"
    "   ██║   ██║   ██║██║╚██╗██║██╔══╝  ██║  ██║██╔══██╗██║   ██║██╔═══╝ "
    "   ██║   ╚██████╔╝██║ ╚████║███████╗██████╔╝██║  ██║╚██████╔╝██║     "
    "   ╚═╝    ╚═════╝ ╚═╝  ╚═══╝╚══════╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚═╝     "
)
ANCHOS=(9 9 10 8 8 8 9 8)    # T U N E D R O P

# Escribe el texto $1 repetido $2 veces.
repetir() {
    local texto="" k
    for ((k = 0; k < $2; k++)); do texto+=$1; done
    printf '%s' "$texto"
}

mostrar_logo() {
    local columnas fila linea inicio n
    columnas=$(tput cols 2>/dev/null || echo 80)
    echo
    if [ "$UNICODE" = 1 ] && [ "$columnas" -ge 72 ]; then
        for fila in "${LOGO[@]}"; do
            linea="  " inicio=0
            for n in "${!ANCHOS[@]}"; do
                linea+="${COLORES[n]}${fila:inicio:ANCHOS[n]}"
                inicio=$((inicio + ANCHOS[n]))
            done
            printf '%s%s\n' "$linea" "$NORMAL"
        done
    else
        # Ventana estrecha: el logo grande no cabría y se descolocaría.
        printf '  %s%s t u n e d r o p %s\n' "$NEGRITA" "${COLORES[0]}" "$NORMAL"
    fi
    printf '\n  %s%s  Tu música en MP3, lista para tu reproductor o iPod%s\n\n' "$TENUE" "$NOTA" "$NORMAL"
}

# Línea de un paso terminado:  ✔ Texto  detalle
hecho() {
    printf '%s  %s%s%s  %s  %s%s%s\n' "$BORRAR_LINEA" "$VERDE" "$BIEN" "$NORMAL" "$1" "$TENUE" "${2:-}" "$NORMAL"
}

# Dibuja un recuadro con esquinas redondeadas alrededor de las líneas de texto.
# Uso: caja COLOR "línea 1" "línea 2" ...
caja() {
    local color=$1 ancho=0 linea
    shift
    for linea in "$@"; do
        if [ "${#linea}" -gt "$ancho" ]; then ancho=${#linea}; fi
    done
    ancho=$((ancho + 4))
    printf '  %s%s%s%s%s\n' "$color" "${CAJA[0]}" "$(repetir "${CAJA[4]}" "$ancho")" "${CAJA[1]}" "$NORMAL"
    for linea in "$@"; do
        printf '  %s%s%s  %s%*s  %s%s%s\n' "$color" "${CAJA[5]}" "$NORMAL" "$linea" \
            $((ancho - 4 - ${#linea})) "" "$color" "${CAJA[5]}" "$NORMAL"
    done
    printf '  %s%s%s%s%s\n' "$color" "${CAJA[2]}" "$(repetir "${CAJA[4]}" "$ancho")" "${CAJA[3]}" "$NORMAL"
}

fallo() {
    printf '%s  %s%s %s%s\n' "$BORRAR_LINEA" "$ROJO" "$MAL" "$1" "$NORMAL" >&2
    if [ -n "${2:-}" ]; then printf '    %s\n' "$2" >&2; fi
    echo >&2
    exit 1
}

# Ejecuta una orden mientras muestra la ruedita girando al lado del texto.
# La salida de la orden se guarda en registro.txt por si hay que ver un error.
# Uso: con_espera "Texto que se ve" orden argumentos...
con_espera() {
    local texto=$1 pid i=0
    shift
    "$@" >"$TEMPORAL/registro.txt" 2>&1 &
    pid=$!
    if [ "$BONITO" = 1 ]; then
        while kill -0 "$pid" 2>/dev/null; do
            printf '%s  %s%s%s  %s' "$BORRAR_LINEA" "$VIOLETA" "${GIRO[i++ % ${#GIRO[@]}]}" "$NORMAL" "$texto"
            sleep 0.1
        done
    fi
    wait "$pid"
}

# Descarga un archivo mostrando una barra de progreso:  ━━━━━━━━━━━━━━━━━━  64 %  128/200 MB
# Uso: descargar URL ARCHIVO
descargar() {
    local url=$1 archivo=$2 total pid bajado llenos i=0
    # Primero preguntamos el tamaño total (la cabecera «content-length»).
    # Si no llega, en vez de la barra se muestran solo los MB descargados.
    total=$(curl -fsSLI "$url" | tr -d '\r' |
        awk 'tolower($1) == "content-length:" { n = $2 } END { print n + 0 }') || total=0
    curl -fsSL "$url" -o "$archivo" &
    pid=$!
    if [ "$BONITO" = 1 ]; then
        while kill -0 "$pid" 2>/dev/null; do
            bajado=0
            if [ -f "$archivo" ]; then bajado=$(wc -c <"$archivo"); fi
            if [ "$total" -gt 0 ]; then
                llenos=$((bajado * 30 / total))
                printf '%s  %s%s%s%s%s  %3d %%  %s%d/%d MB%s' "$BORRAR_LINEA" \
                    "$VIOLETA" "$(repetir "$BARRA" "$llenos")" "$GRIS" "$(repetir "$BARRA" $((30 - llenos)))" "$NORMAL" \
                    $((bajado * 100 / total)) "$TENUE" $((bajado / 1048576)) $((total / 1048576)) "$NORMAL"
            else
                printf '%s  %s%s%s  Descargando  %s%d MB%s' "$BORRAR_LINEA" \
                    "$VIOLETA" "${GIRO[i++ % ${#GIRO[@]}]}" "$NORMAL" "$TENUE" $((bajado / 1048576)) "$NORMAL"
            fi
            sleep 0.2
        done
    else
        echo "  Descargando ..."
    fi
    wait "$pid"
}

# Al terminar (bien, mal o con Ctrl+C): borrar la carpeta temporal y volver a
# mostrar el cursor, que se esconde durante las animaciones para que no parpadee.
limpiar() {
    if [ -n "$TEMPORAL" ]; then rm -rf "$TEMPORAL"; fi
    if [ "$BONITO" = 1 ]; then printf '\033[?25h'; fi
}
trap limpiar EXIT
trap 'echo; exit 130' INT TERM
if [ "$BONITO" = 1 ]; then printf '\033[?25l'; fi

mostrar_logo
TEMPORAL=$(mktemp -d)

# ============================================================
#  Desinstalar
# ============================================================
# Solo borra lo que este script creó. Tu música no se toca.
if [ "${1:-}" = "--desinstalar" ]; then
    con_espera "Quitando tunedrop" rm -rf "$DESTINO" "$MENU" "$COMANDO"
    hecho "tunedrop se ha desinstalado"
    echo
    caja "$VERDE" "Tu música sigue en su carpeta." "¡Gracias por usar tunedrop!"
    echo
    exit 0
fi

# ============================================================
#  Instalar
# ============================================================

# --- NixOS -------------------------------------------------------
# NixOS guarda las librerías en otro sitio y el programa compilado no funciona
# allí. En NixOS, tunedrop se instala con Nix (ver flake.nix en el repositorio).
if [ -e /etc/NIXOS ] || grep -qs '^ID=nixos' /etc/os-release; then
    caja "$VIOLETA" \
        "$NOTA  Estás en NixOS: allí tunedrop se instala con Nix." \
        "" \
        "   Para instalarlo para siempre, mira la guía:" \
        "   https://github.com/$REPO#nixos"
    echo
    # El comando va fuera del recuadro para poder copiarlo sin los bordes.
    echo "  Para probarlo sin instalar nada, copia esta línea:"
    echo
    printf '    %s%s%s\n\n' "$NEGRITA" "nix --extra-experimental-features 'nix-command flakes' run github:$REPO" "$NORMAL"
    exit 0
fi

# --- Comprobaciones --------------------------------------------
command -v curl >/dev/null || fallo "Hace falta curl." "Instálalo con: sudo apt install curl (o el gestor de tu distribución)."
command -v tar >/dev/null || fallo "Hace falta tar."
[ "$(uname -m)" = "x86_64" ] || fallo "De momento solo hay versión para PC de 64 bits (x86_64). Tu equipo es $(uname -m)." \
    "Puedes ejecutarlo desde el código: https://github.com/$REPO#para-programadores"

# --- 1. Buscar la última versión --------------------------------
# La página .../releases/latest redirige a la última versión, por ejemplo
# .../releases/tag/v0.1.0. Nos quedamos con el final («v0.1.0»).
# No usamos la API de GitHub porque solo permite 60 consultas por hora
# desde la misma red (en un aula, varios alumnos se quedarían sin instalar).
buscar_version() {
    curl -fsSLI -o /dev/null -w '%{url_effective}' "https://github.com/$REPO/releases/latest"
}
con_espera "Buscando la última versión" buscar_version || true
FINAL=$(cat "$TEMPORAL/registro.txt")
ETIQUETA="${FINAL##*/}"          # todo lo que va después de la última «/»
case "$ETIQUETA" in
    v*) ;;                        # es una versión: seguimos
    *) fallo "No se encontró ninguna versión publicada." "Comprueba tu conexión o mira https://github.com/$REPO/releases" ;;
esac
VERSION="${ETIQUETA#v}"          # «v0.1.0» -> «0.1.0»
ARCHIVO="tunedrop-$VERSION-linux-x86_64.tar.gz"
URL="https://github.com/$REPO/releases/download/$ETIQUETA/$ARCHIVO"
hecho "Última versión encontrada" "$ETIQUETA"

# --- 2. Descargar ------------------------------------------------
descargar "$URL" "$TEMPORAL/tunedrop.tar.gz" ||
    fallo "No se pudo descargar $ARCHIVO." "Comprueba tu conexión a internet y vuelve a intentarlo."
hecho "Descargado" "$(($(wc -c <"$TEMPORAL/tunedrop.tar.gz") / 1048576)) MB"

# --- 3. Instalar (sustituye la versión anterior si la hay) -------
instalar() {
    # Con «&&» cada orden solo se ejecuta si la anterior ha ido bien.
    tar -xzf "$TEMPORAL/tunedrop.tar.gz" -C "$TEMPORAL" &&
        [ -x "$TEMPORAL/tunedrop/tunedrop" ] &&
        rm -rf "$DESTINO" &&
        mkdir -p "$(dirname "$DESTINO")" &&
        mv "$TEMPORAL/tunedrop" "$DESTINO"
}
con_espera "Instalando" instalar || fallo "El archivo descargado no tiene el formato esperado."
hecho "Instalado" "${DESTINO/#$HOME/\~}"     # ~ en vez de /home/usuario: más corto

# --- 4. Menú de aplicaciones y comando ---------------------------
# Un archivo .desktop es el «acceso directo» de los escritorios de Linux
# (GNOME, KDE, XFCE...). Hace que tunedrop aparezca como cualquier otra app.
crear_accesos() {
    mkdir -p "$(dirname "$MENU")" "$(dirname "$COMANDO")"
    cat >"$MENU" <<EOF
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
    if command -v update-desktop-database >/dev/null; then
        update-desktop-database "$(dirname "$MENU")" 2>/dev/null || true
    fi
}
con_espera "Añadiendo tunedrop al menú de aplicaciones" crear_accesos
hecho "Añadido al menú de aplicaciones" "y el comando «tunedrop»"
echo

# --- Librería del sistema que necesita Qt -------------------------
# La ventana usa Qt, que necesita libxcb-cursor. Falta en algunas instalaciones mínimas.
if command -v ldconfig >/dev/null && ! ldconfig -p | grep -q libxcb-cursor; then
    caja "$AMARILLO" \
        "$AVISO  Falta libxcb-cursor, una librería que la ventana necesita." \
        "   Instálala con el comando de tu distribución:" \
        "" \
        "   Ubuntu/Debian:  sudo apt install libxcb-cursor0" \
        "   Fedora:         sudo dnf install xcb-util-cursor" \
        "   Arch:           sudo pacman -S xcb-util-cursor"
    echo
fi

# --- Listo ---------------------------------------------------------
# ~/.local/bin solo entra en el PATH (la lista de carpetas donde la terminal
# busca comandos) al iniciar sesión, y solo si ya existía. Si es nueva, avisamos.
case ":$PATH:" in
    *":$HOME/.local/bin:"*) PISTA="o escribe en la terminal:  tunedrop" ;;
    *) PISTA="(el comando «tunedrop» funcionará al volver a iniciar sesión)" ;;
esac
caja "$VERDE" \
    "$BIEN  ¡Listo! tunedrop $VERSION está instalado." \
    "" \
    "   Ábrelo desde el menú de aplicaciones" \
    "   $PISTA"
echo
