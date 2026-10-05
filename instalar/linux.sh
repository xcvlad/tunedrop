#!/usr/bin/env bash
# ============================================================
#  Instalador de tunedrop para Linux en un solo comando.
#
#  Se usa así (copiar y pegar en una terminal):
#      curl -fsSL https://raw.githubusercontent.com/xcvlad/tunedrop/main/instalar/linux.sh | bash
#
#  Qué hace:
#  0. Pregunta el idioma (español o inglés): el de este instalador y el de
#     la app. Sale marcado el que ya tenías (o, la primera vez, el del
#     sistema), así que para no cambiarlo basta con pulsar Intro.
#  1. Busca la última versión publicada en GitHub (Releases).
#  2. Descarga el programa ya compilado (no necesitas Python).
#  3. Lo guarda en ~/.local/share/tunedrop, solo para tu usuario (sin sudo).
#  4. Lo añade al menú de aplicaciones y crea el comando «tunedrop».
#
#  En NixOS no instala nada: explica cómo hacerlo con Nix (flake.nix).
#
#  Volver a ejecutarlo actualiza a la última versión.
#  Para elegir el idioma sin que pregunte, pon TUNEDROP_IDIOMA=es (o en) delante
#  de «bash»:  curl -fsSL ... | TUNEDROP_IDIOMA=en bash
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
# El idioma elegido se guarda donde lo busca la app (ver tunedrop/idioma.py).
ARCHIVO_IDIOMA="${XDG_CONFIG_HOME:-$HOME/.config}/tunedrop/idioma.txt"
IDIOMA="es"                                       # «es» o «en» (se decide más abajo)

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

# ============================================================
#  Idioma: español o inglés
# ============================================================

# Cada texto va en los dos idiomas, y «t» escribe el que toca:
#   t "Instalando" "Installing"   ->  «Instalando» o «Installing»
t() {
    if [ "$IDIOMA" = "en" ]; then printf '%s' "$2"; else printf '%s' "$1"; fi
}

# Decide el idioma de este instalador y de la app.
# - Si existe la variable TUNEDROP_IDIOMA (la pone la app al actualizarse), se
#   usa esa y no se pregunta.
# - Si no, el que ya tenías (idioma.txt; lo escribe también la app en Ajustes)
#   o, la primera vez, el del sistema. Si se llama con «preguntar» y hay
#   alguien delante (una terminal), se pregunta siempre, con ese ya marcado
#   (basta con pulsar Intro).
elegir_idioma() {
    local elegido="${TUNEDROP_IDIOMA:-}" marcado respuesta=""
    case "$elegido" in
        es | en) IDIOMA=$elegido; return 0 ;;
    esac
    if [ -f "$ARCHIVO_IDIOMA" ]; then
        elegido=$(tr -d ' \r\n' <"$ARCHIVO_IDIOMA" | tr '[:upper:]' '[:lower:]') || elegido=""
    fi
    case "$elegido" in
        es | en) IDIOMA=$elegido ;;
        *)
            # El idioma del sistema sale de estas variables (valen cosas como «es_ES.UTF-8»).
            case "${LANGUAGE:-${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}}" in
                es*) IDIOMA="es" ;;
                *) IDIOMA="en" ;;
            esac ;;
    esac
    if [ "$IDIOMA" = "en" ]; then marcado=2; else marcado=1; fi
    # La respuesta se lee de la terminal (/dev/tty), porque este script llega por «curl | bash».
    if [ "${1:-}" = "preguntar" ] && { true </dev/tty; } 2>/dev/null; then
        printf '  Idioma / Language\n\n'
        printf '    %s1%s  Español\n' "$VIOLETA" "$NORMAL"
        printf '    %s2%s  English\n\n' "$VIOLETA" "$NORMAL"
        if [ "$BONITO" = 1 ]; then printf '\033[?25h'; fi    # cursor visible para escribir
        printf '  1 / 2 [%s] ' "$marcado"
        read -r respuesta </dev/tty || respuesta=""
        if [ "$BONITO" = 1 ]; then printf '\033[?25l'; fi
        echo
        case "$respuesta" in
            1) IDIOMA="es" ;;
            2) IDIOMA="en" ;;
        esac                                 # cualquier otra cosa: el marcado
    fi
}

# Guarda el idioma para la app.
guardar_idioma() {
    mkdir -p "$(dirname "$ARCHIVO_IDIOMA")" && printf '%s\n' "$IDIOMA" >"$ARCHIVO_IDIOMA"
}

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
    echo
}

mostrar_lema() {
    printf '  %s%s  %s%s\n\n' "$TENUE" "$NOTA" \
        "$(t "Tu música en MP3, lista para tu reproductor o iPod" "Your music as MP3, ready for your player or iPod")" "$NORMAL"
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
                printf '%s  %s%s%s  %s  %s%d MB%s' "$BORRAR_LINEA" \
                    "$VIOLETA" "${GIRO[i++ % ${#GIRO[@]}]}" "$NORMAL" "$(t "Descargando" "Downloading")" \
                    "$TENUE" $((bajado / 1048576)) "$NORMAL"
            fi
            sleep 0.2
        done
    else
        echo "  $(t "Descargando" "Downloading") ..."
    fi
    wait "$pid"
}

# ============================================================
#  Librerías del sistema y el comando «tunedrop»
# ============================================================

# El programa lleva dentro casi todas sus librerías, pero algunas tiene que
# ponerlas el sistema: sobre todo las de gráficos (libEGL, libGL), que dependen
# de la tarjeta gráfica de cada ordenador. «ldd» es la herramienta de Linux que
# dice qué librerías necesita un programa y si las encuentra. Revisando las
# piezas de tunedrop con ella se sabe exactamente qué falta, en cualquier distribución.
# Escribe una librería que falta por línea (nada si no falta ninguna).
librerias_que_faltan() {
    local interno="$DESTINO/_internal" archivos=() f
    for f in "$interno"/libpython3*.so* \
             "$interno"/libQt6{Core,Gui,Widgets,Network,Svg,Multimedia,XcbQpa,DBus,OpenGL}.so.6 \
             "$interno"/PySide6/Qt/plugins/platforms/libqxcb.so \
             "$interno"/PySide6/Qt/plugins/multimedia/libffmpegmediaplugin.so \
             "$interno"/libtk8.6.so; do      # la usa la pantalla de carga
        if [ -e "$f" ]; then archivos+=("$f"); fi
    done
    if [ "${#archivos[@]}" -eq 0 ]; then return 0; fi
    # Las líneas de lo que falta son así:  «libEGL.so.1 => not found»
    listar_librerias "$interno" "${archivos[@]}" 2>/dev/null |
        awk '$2 == "=>" && $3 == "not" { print $1 }' | sort -u
}

# Lista las librerías que usan unos archivos, buscando también en la carpeta de
# tunedrop. Uso: listar_librerias CARPETA archivo...
# Se pregunta directamente al «cargador» de programas de Linux, que es lo que
# ldd hace por dentro. No se usa ldd porque es un script de bash: si se le pasa
# la carpeta de tunedrop con LD_LIBRARY_PATH, el propio bash intenta usar las
# librerías de tunedrop y en algunas distribuciones (Arch, openSUSE) se cae. Así,
# LD_LIBRARY_PATH solo le llega al cargador. LD_TRACE_LOADED_OBJECTS=1 le pide
# que liste todas las librerías sin cargar el programa (con «--list», en cambio,
# se para en la primera que falta).
listar_librerias() {
    local carpeta=$1 f
    shift
    if [ -x /lib64/ld-linux-x86-64.so.2 ]; then
        for f in "$@"; do
            LD_TRACE_LOADED_OBJECTS=1 LD_LIBRARY_PATH="$carpeta" /lib64/ld-linux-x86-64.so.2 "$f" || true
        done
    elif command -v ldd >/dev/null; then
        LD_LIBRARY_PATH="$carpeta" ldd "$@" || true
    fi
}

# El gestor de paquetes de la distribución, para dar el comando exacto.
# /etc/os-release dice qué distribución es (ID) y en cuál se basa (ID_LIKE):
# Linux Mint, por ejemplo, tiene ID=linuxmint e ID_LIKE="ubuntu debian".
GESTOR=""
DISTRO=" $(. /etc/os-release 2>/dev/null; echo "${ID:-} ${ID_LIKE:-}") "
case "$DISTRO" in
    *" debian "* | *" ubuntu "*) GESTOR="apt" ;;
    *" fedora "* | *" rhel "*) GESTOR="dnf" ;;
    *" arch "*) GESTOR="pacman" ;;
    *" suse "* | *" opensuse "*) GESTOR="zypper" ;;
esac

# El paquete que instala una librería en cada distribución (vacío si no se sabe).
paquete_de() {
    local nombre="${1%%.so.*}" version="${1##*.so.}"
    case "$GESTOR" in
        apt)
            # Debian, Ubuntu y Mint siguen una regla: el paquete se llama como la
            # librería, en minúsculas, más su número de versión (con un guion si el
            # nombre acaba en número):
            #   libEGL.so.1 -> libegl1    libxcb-icccm.so.4 -> libxcb-icccm4    libxkbcommon-x11.so.0 -> libxkbcommon-x11-0
            case "$nombre" in *[0-9]) nombre="$nombre-" ;; esac
            printf '%s%s\n' "$(printf '%s' "$nombre" | tr '[:upper:]' '[:lower:]')" "$version" ;;
        dnf | zypper)
            # Fedora y openSUSE dejan pedir un paquete por la librería que contiene:
            # el gestor busca solo qué paquete la trae (vale para cualquier librería).
            echo "$1()(64bit)" ;;
        pacman)
            # En Arch no hay regla: los nombres van uno a uno.
            case "$nombre" in
                libEGL | libGL | libGLX | libOpenGL) echo libglvnd ;;
                libxcb | libxcb-shape | libxcb-xfixes | libxcb-shm | libxcb-randr | libxcb-sync | libxcb-xkb | libxcb-render)
                    echo libxcb ;;
                libxcb-icccm) echo xcb-util-wm ;;
                libxcb-keysyms) echo xcb-util-keysyms ;;
                libxcb-image) echo xcb-util-image ;;
                libxcb-render-util) echo xcb-util-renderutil ;;
                libxcb-cursor) echo xcb-util-cursor ;;
                libxkbcommon) echo libxkbcommon ;;
                libxkbcommon-x11) echo libxkbcommon-x11 ;;
                libdrm) echo libdrm ;;
                libfontconfig) echo fontconfig ;;
                libfreetype) echo freetype2 ;;
                libpulse) echo libpulse ;;
            esac ;;
    esac
}

# La orden para instalar paquetes con el gestor de la distribución.
orden_instalar() {
    case "$GESTOR" in
        apt) echo "sudo apt install -y" ;;
        dnf) echo "sudo dnf install -y" ;;
        pacman) echo "sudo pacman -S --needed --noconfirm" ;;
        zypper) echo "sudo zypper install -y" ;;
    esac
}

# ~/.local/bin es la carpeta estándar para los comandos de cada usuario, pero en
# Ubuntu, Linux Mint y otras solo entra en el PATH (la lista de carpetas donde la
# terminal busca comandos) al iniciar sesión, y solo si ya existía. Para no tener
# que cerrar sesión, se añade a la configuración de la terminal (bash, zsh y
# fish): las terminales que abras a partir de ahora ya la tendrán.
anadir_al_path() {
    local linea='export PATH="$HOME/.local/bin:$PATH"  # añadido por el instalador de tunedrop' rc
    local terminal="${SHELL:-}"
    if [ "${terminal##*/}" = "bash" ] && [ ! -f "$HOME/.bashrc" ]; then
        touch "$HOME/.bashrc"      # sin él, bash no tendría dónde leer la línea
    fi
    for rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
        # Solo si ese archivo existe y no menciona ya ~/.local/bin.
        if [ -f "$rc" ] && ! grep -qs '\.local/bin' "$rc"; then
            printf '\n%s\n' "$linea" >>"$rc"
        fi
    done
    if command -v fish >/dev/null; then
        mkdir -p "$HOME/.config/fish/conf.d"
        echo 'fish_add_path -g "$HOME/.local/bin"  # añadido por el instalador de tunedrop' \
            >"$HOME/.config/fish/conf.d/tunedrop.fish"
    fi
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

# NixOS guarda las librerías en otro sitio y el programa compilado no funciona
# allí. En NixOS, tunedrop se instala con Nix (ver flake.nix en el repositorio).
ES_NIXOS=0
if [ -e /etc/NIXOS ] || grep -qs '^ID=nixos' /etc/os-release; then ES_NIXOS=1; fi

# --- 0. Idioma ---------------------------------------------------
# Solo se pregunta si se va a instalar (no al desinstalar ni en NixOS).
if [ "${1:-}" != "--desinstalar" ] && [ "$ES_NIXOS" = 0 ]; then
    elegir_idioma preguntar
else
    elegir_idioma
fi
mostrar_lema

# ============================================================
#  Desinstalar
# ============================================================
# Solo borra lo que este script creó. Tu música no se toca.
if [ "${1:-}" = "--desinstalar" ]; then
    con_espera "$(t "Quitando tunedrop" "Removing tunedrop")" rm -rf "$DESTINO" "$MENU" "$COMANDO"
    hecho "$(t "tunedrop se ha desinstalado" "tunedrop has been uninstalled")"
    echo
    caja "$VERDE" "$(t "Tu música sigue en su carpeta." "Your music is still in its folder.")" \
        "$(t "¡Gracias por usar tunedrop!" "Thanks for using tunedrop!")"
    echo
    exit 0
fi

# ============================================================
#  Instalar
# ============================================================

# --- NixOS (ver ES_NIXOS, arriba) ---------------------------------
if [ "$ES_NIXOS" = 1 ]; then
    caja "$VIOLETA" \
        "$NOTA  $(t "Estás en NixOS: allí tunedrop se instala con Nix." "You're on NixOS: there, tunedrop is installed with Nix.")" \
        "" \
        "   $(t "Para instalarlo para siempre, mira la guía:" "To install it for good, see the guide:")" \
        "   https://github.com/$REPO#nixos"
    echo
    # El comando va fuera del recuadro para poder copiarlo sin los bordes.
    echo "  $(t "Para probarlo sin instalar nada, copia esta línea:" "To try it without installing anything, copy this line:")"
    echo
    printf '    %s%s%s\n\n' "$NEGRITA" "nix --extra-experimental-features 'nix-command flakes' run github:$REPO" "$NORMAL"
    exit 0
fi

# --- Comprobaciones --------------------------------------------
command -v curl >/dev/null || fallo "$(t "Hace falta curl." "curl is needed.")" \
    "$(t "Instálalo con: sudo apt install curl (o el gestor de tu distribución)." "Install it with: sudo apt install curl (or your distribution's package manager).")"
command -v tar >/dev/null || fallo "$(t "Hace falta tar." "tar is needed.")"
[ "$(uname -m)" = "x86_64" ] || fallo "$(t "De momento solo hay versión para PC de 64 bits (x86_64). Tu equipo es" "For now there's only a version for 64-bit PCs (x86_64). Yours is") $(uname -m)." \
    "$(t "Puedes ejecutarlo desde el código:" "You can run it from the source code:") https://github.com/$REPO#para-programadores"

# glibc es la librería básica de Linux, y cada distribución trae la suya. El
# programa se compila en Ubuntu 22.04 (ver .github/workflows/release.yml) y
# necesita su glibc (2.35) o una más nueva. Con una más antigua no arrancaría,
# así que mejor avisar antes de descargar nada.
GLIBC_MINIMA="2.35"
# «getconf GNU_LIBC_VERSION» responde «glibc 2.35». Si no, se pregunta a ldd.
GLIBC=$(getconf GNU_LIBC_VERSION 2>/dev/null | awk '{ print $2 }') || GLIBC=""
if [ -z "$GLIBC" ]; then
    GLIBC=$(ldd --version 2>/dev/null | awk 'NR == 1 { print $NF }') || GLIBC=""
fi
case "$GLIBC" in
    [0-9]*.[0-9]*)
        if [ "$(printf '%s\n%s\n' "$GLIBC_MINIMA" "$GLIBC" | sort -V | awk 'NR == 1')" != "$GLIBC_MINIMA" ]; then
            fallo "$(t "Tu Linux es demasiado antiguo para esta versión de tunedrop (tiene glibc" "Your Linux is too old for this version of tunedrop (it has glibc") $GLIBC)." \
                "$(t "Necesita Ubuntu 22.04, Linux Mint 21, Debian 12, Fedora 36 o más nuevos." "It needs Ubuntu 22.04, Linux Mint 21, Debian 12, Fedora 36 or newer.")
    $(t "Otra opción es instalarlo con Nix:" "Another option is to install it with Nix:") https://github.com/$REPO#nixos"
        fi ;;
esac

# --- 1. Buscar la última versión --------------------------------
# La página .../releases/latest redirige a la última versión, por ejemplo
# .../releases/tag/v0.1.0. Nos quedamos con el final («v0.1.0»).
# No usamos la API de GitHub porque solo permite 60 consultas por hora
# desde la misma red (en un aula, varios alumnos se quedarían sin instalar).
buscar_version() {
    curl -fsSLI -o /dev/null -w '%{url_effective}' "https://github.com/$REPO/releases/latest"
}
con_espera "$(t "Buscando la última versión" "Looking for the latest version")" buscar_version || true
FINAL=$(cat "$TEMPORAL/registro.txt")
ETIQUETA="${FINAL##*/}"          # todo lo que va después de la última «/»
case "$ETIQUETA" in
    v*) ;;                        # es una versión: seguimos
    *) fallo "$(t "No se encontró ninguna versión publicada." "No published version was found.")" \
        "$(t "Comprueba tu conexión o mira" "Check your connection or see") https://github.com/$REPO/releases" ;;
esac
VERSION="${ETIQUETA#v}"          # «v0.1.0» -> «0.1.0»
ARCHIVO="tunedrop-$VERSION-linux-x86_64.tar.gz"
URL="https://github.com/$REPO/releases/download/$ETIQUETA/$ARCHIVO"
hecho "$(t "Última versión encontrada" "Latest version found")" "$ETIQUETA"

# --- 2. Descargar ------------------------------------------------
descargar "$URL" "$TEMPORAL/tunedrop.tar.gz" ||
    fallo "$(t "No se pudo descargar" "Couldn't download") $ARCHIVO." \
        "$(t "Comprueba tu conexión a internet y vuelve a intentarlo." "Check your internet connection and try again.")"
hecho "$(t "Descargado" "Downloaded")" "$(($(wc -c <"$TEMPORAL/tunedrop.tar.gz") / 1048576)) MB"

# --- 3. Instalar (sustituye la versión anterior si la hay) -------
instalar() {
    # Con «&&» cada orden solo se ejecuta si la anterior ha ido bien.
    tar -xzf "$TEMPORAL/tunedrop.tar.gz" -C "$TEMPORAL" &&
        [ -x "$TEMPORAL/tunedrop/tunedrop" ] &&
        rm -rf "$DESTINO" &&
        mkdir -p "$(dirname "$DESTINO")" &&
        mv "$TEMPORAL/tunedrop" "$DESTINO"
}
con_espera "$(t "Instalando" "Installing")" instalar ||
    fallo "$(t "El archivo descargado no tiene el formato esperado." "The downloaded file doesn't have the expected format.")"
guardar_idioma || true          # si no se puede guardar, la app usará el del sistema
hecho "$(t "Instalado" "Installed")" "${DESTINO/#$HOME/\~}"     # ~ en vez de /home/usuario: más corto

# --- 4. Menú de aplicaciones y comando ---------------------------
# Un archivo .desktop es el «acceso directo» de los escritorios de Linux
# (GNOME, KDE, XFCE...). Hace que tunedrop aparezca como cualquier otra app.
crear_accesos() {
    mkdir -p "$(dirname "$MENU")" "$(dirname "$COMANDO")"
    cat >"$MENU" <<EOF
[Desktop Entry]
Type=Application
Name=tunedrop
Comment=Download music as MP3 with title, artist and cover art
Comment[es]=Descarga música en MP3 con título, artista y carátula
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
con_espera "$(t "Añadiendo tunedrop al menú de aplicaciones" "Adding tunedrop to the applications menu")" crear_accesos
hecho "$(t "Añadido al menú de aplicaciones" "Added to the applications menu")" "$(t "y el comando «tunedrop»" "and the “tunedrop” command")"
echo

# --- 5. Librerías del sistema --------------------------------------
# Solo se avisa de lo que falta de verdad (ver librerias_que_faltan, arriba).
FALTAN=$(librerias_que_faltan) || FALTAN=""
if [ -n "$FALTAN" ]; then
    PAQUETES="" DESCONOCIDAS=""
    for lib in $FALTAN; do
        paquete=$(paquete_de "$lib")
        if [ -z "$paquete" ]; then
            DESCONOCIDAS="$DESCONOCIDAS $lib"
        else
            case " $PAQUETES " in *" $paquete "*) ;; *) PAQUETES="${PAQUETES:+$PAQUETES }$paquete" ;; esac
        fi
    done
    lineas=("$AVISO  $(t "A tu sistema le faltan librerías que tunedrop necesita:" "Your system is missing libraries that tunedrop needs:")" "")
    for lib in $FALTAN; do lineas+=("     $lib"); done
    caja "$AMARILLO" "${lineas[@]}"
    echo
    # ORDEN es lo que se ejecuta; ORDEN_TEXTO, lo que se enseña para copiarlo: los
    # nombres con paréntesis (Fedora, openSUSE) van entre comillas para la terminal.
    ORDEN="" ORDEN_TEXTO=""
    if [ -n "$PAQUETES" ] && [ -n "$(orden_instalar)" ]; then
        ORDEN="$(orden_instalar) $PAQUETES"
        ORDEN_TEXTO="$(orden_instalar)"
        for paquete in $PAQUETES; do
            case "$paquete" in
                *"("*) ORDEN_TEXTO="$ORDEN_TEXTO '$paquete'" ;;
                *) ORDEN_TEXTO="$ORDEN_TEXTO $paquete" ;;
            esac
        done
    fi

    # Si sabemos qué paquetes son, se ofrece instalarlos ahora. La respuesta se
    # lee de la terminal (/dev/tty), porque este script llega por «curl | bash».
    if [ -n "$ORDEN" ] && [ -z "$DESCONOCIDAS" ] && command -v sudo >/dev/null &&
        { true </dev/tty; } 2>/dev/null; then
        if [ "$BONITO" = 1 ]; then printf '\033[?25h'; fi    # cursor visible para escribir
        printf '  %s  %s%s%s\n\n' "$(t "Se instalan con:" "They're installed with:")" "$NEGRITA" "$ORDEN_TEXTO" "$NORMAL"
        printf '  %s ' "$(t "¿Las instalo ahora? Te pedirá tu contraseña. [S/n]" "Install them now? It will ask for your password. [Y/n]")"
        read -r respuesta </dev/tty || respuesta="n"
        echo
        case "$respuesta" in
            [nN]*) ;;
            *) $ORDEN </dev/tty || true ;;
        esac
        echo
    else
        if [ -n "$ORDEN" ]; then
            printf '  %s  %s%s%s\n\n' "$(t "Instálalas con:" "Install them with:")" "$NEGRITA" "$ORDEN_TEXTO" "$NORMAL"
        fi
        if [ -n "$DESCONOCIDAS" ]; then
            echo "  $(t "Con el gestor de paquetes de tu distribución, busca qué paquete" "With your distribution's package manager, look for the package")"
            echo "  $(t "contiene cada una de estas:" "that contains each of these:")$DESCONOCIDAS"
            echo
        fi
    fi

    # ¿Siguen faltando?
    FALTAN=$(librerias_que_faltan) || FALTAN=""
    if [ -z "$FALTAN" ]; then
        hecho "$(t "Librerías del sistema instaladas" "System libraries installed")"
        echo
    fi
fi

# --- Listo ---------------------------------------------------------
# El comando «tunedrop» está en ~/.local/bin. Si esta terminal ya la tiene en el
# PATH, funciona ya; si no, se añade para las terminales nuevas (anadir_al_path).
case ":$PATH:" in
    *":$HOME/.local/bin:"*) PISTA=$(t "o escribe en la terminal:  tunedrop" "or type in the terminal:  tunedrop") ;;
    *)
        anadir_al_path
        PISTA=$(t "o abre una terminal nueva y escribe:  tunedrop" "or open a new terminal and type:  tunedrop") ;;
esac
if [ -z "$FALTAN" ]; then
    caja "$VERDE" \
        "$BIEN  $(t "¡Listo! tunedrop $VERSION está instalado." "Done! tunedrop $VERSION is installed.")" \
        "" \
        "   $(t "Ábrelo desde el menú de aplicaciones" "Open it from the applications menu")" \
        "   $PISTA"
else
    caja "$AMARILLO" \
        "$AVISO  $(t "tunedrop $VERSION está instalado, pero le faltan" "tunedrop $VERSION is installed, but it's missing")" \
        "   $(t "las librerías de arriba." "the libraries above.")" \
        "" \
        "   $(t "Cuando las instales, ábrelo desde el menú de aplicaciones" "Once you install them, open it from the applications menu")" \
        "   $PISTA"
fi
echo
