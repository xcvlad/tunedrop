"""Idioma de la app: español o inglés.

Cómo se traduce
---------------
En el código, los textos se escriben en español dentro de tr():

    tr("Buscar")                    ->  «Buscar» o «Search»
    tr("{n} canciones", n=3)        ->  «3 canciones» o «3 songs»

Lo que va entre llaves se rellena después de traducir, así la traducción
puede cambiar el orden de las palabras. Las traducciones están en el
diccionario INGLES, al final de este archivo: la clave es el texto en español
y el valor, el mismo texto en inglés. Si falta alguna, se ve en español, y el
test test_todos_los_textos_traducidos avisa.

Qué idioma se usa
-----------------
1. El que elegiste en Ajustes o al instalar, guardado en idioma.txt, en la
   carpeta de configuración (junto a settings.json). Va en un archivo aparte,
   con solo «es» o «en», para que los instaladores (PowerShell, bash e Inno
   Setup) lo puedan escribir con una línea, sin tener que editar un JSON.
2. Si no hay, el del sistema: español si tu sistema está en español; si no, inglés.

El idioma se decide al abrir la app; para cambiarlo hay que volver a abrirla.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

IDIOMAS = {"es": "Español", "en": "English"}

_actual: str | None = None      # el idioma de esta sesión (se decide la primera vez que se pide)


def archivo() -> Path:
    """El archivo donde se guarda el idioma elegido."""
    from .core.settings import data_dir   # aquí dentro: core también usa este módulo

    return data_dir() / "idioma.txt"


def idioma_guardado() -> str | None:
    """El idioma elegido en Ajustes o al instalar, o None si no se ha elegido."""
    try:
        codigo = archivo().read_text(encoding="utf-8-sig").strip().lower()
    except OSError:
        return None
    return codigo if codigo in IDIOMAS else None


def guardar_idioma(codigo: str) -> None:
    archivo().write_text(codigo + "\n", encoding="utf-8")


def idioma_del_sistema() -> str:
    """«es» si el sistema está en español; si no, «en»."""
    if sys.platform == "win32":
        try:
            import ctypes

            # El idioma de los menús de Windows. Es un número: los 10 bits de
            # abajo dicen el idioma (0x0A = español, de cualquier país).
            numero = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return "es" if numero & 0x3FF == 0x0A else "en"
        except Exception:
            return "en"
    # Linux: las variables de entorno del idioma, por orden de importancia.
    # Valen cosas como «es_ES.UTF-8», «es:en» o «C» (sin idioma).
    for variable in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        valor = os.environ.get(variable)
        if valor:
            return "es" if valor.lower().startswith("es") else "en"
    return "en"


def actual() -> str:
    """El idioma de esta sesión: «es» o «en»."""
    global _actual
    if _actual is None:
        _actual = idioma_guardado() or idioma_del_sistema()
    return _actual


def elegir(codigo: str) -> None:
    """Fija el idioma de esta sesión (lo usan los tests)."""
    global _actual
    _actual = codigo


def tr(texto: str, idioma: str | None = None, **datos) -> str:
    """El texto en el idioma de la app, con los {datos} ya rellenos."""
    if (idioma or actual()) == "en":
        texto = INGLES.get(texto, texto)
    return texto.format(**datos) if datos else texto


# Español -> inglés, agrupado por la parte de la app donde sale cada texto.
INGLES = {
    # --- Ventana principal (ui/main_window.py) ---
    "Busca, elige y descarga tu música lista para cualquier reproductor":
        "Search, pick and download your music, ready for any player",
    "Ajustes": "Settings",
    "Busca una canción o artista… o pega un enlace de YouTube, playlist, SoundCloud, Bandcamp":
        "Search for a song or artist… or paste a YouTube, playlist, SoundCloud or Bandcamp link",
    "Buscar": "Search",
    "Buscando…": "Searching…",
    "Leyendo el enlace…": "Reading the link…",
    "Resultados": "Results",
    "Añadir todas": "Add all",
    "Escribe arriba lo que quieras escuchar y pulsa Intro.\n\n"
    "También puedes pegar o arrastrar aquí un enlace a un vídeo, una playlist o un álbum.":
        "Type what you want to listen to above and press Enter.\n\n"
        "You can also paste or drop a link to a video, a playlist or an album here.",
    "No se encontró nada. Prueba con otras palabras.": "Nothing found. Try other words.",
    "No se pudo buscar: {motivo}": "Couldn't search: {motivo}",
    "{n} canción": "{n} song",
    "{n} canciones": "{n} songs",
    "Tu lista": "Your list",
    "Limpiar completadas": "Clear finished",
    "Abrir la carpeta de música": "Open the music folder",
    "Pulsa + en las canciones que quieras\ny aparecerán aquí.":
        "Press + on the songs you want\nand they'll show up here.",
    "Formato de salida": "Output format",
    "{n} canciones añadidas a tu lista": "{n} songs added to your list",
    "Ya estaban todas en tu lista": "They were all in your list already",
    "{n} listas": "{n} done",
    "Descargar": "Download",
    "Descargar ({n})": "Download ({n})",
    "Descargando {n}…": "Downloading {n}…",
    "Descargas terminadas": "Downloads finished",
    "Falta ffmpeg": "ffmpeg is missing",
    "Ese archivo ya no existe": "That file no longer exists",
    "Enlace copiado: {enlace}  ·  Pulsa para abrirlo": "Copied link: {enlace}  ·  Click to open it",
    "Descargas en curso": "Downloads in progress",
    "Hay {n} descargas en curso. ¿Salir y cancelarlas?":
        "There are {n} downloads in progress. Quit and cancel them?",
    "No se pudo escuchar: {motivo}": "Couldn't play it: {motivo}",
    "Idioma": "Language",
    "tunedrop se verá en español al volver a abrirla.": "tunedrop will be in English when you open it again.",
    "Reiniciar ahora": "Restart now",
    "Más tarde": "Later",

    # --- Tarjetas de canciones (ui/widgets.py) ---
    "Ya descargada": "Already downloaded",
    "Añadir a la lista": "Add to the list",
    "Quitar de la lista": "Remove from the list",
    "Escuchar": "Listen",
    "Parar": "Stop",
    "Cargando…": "Loading…",
    "Cargando… (pulsa para cancelar)": "Loading… (click to cancel)",
    "Quitar": "Remove",
    "Mostrar en la carpeta": "Show in folder",
    "Error: {motivo}": "Error: {motivo}",
    "Reintentar": "Retry",
    # Etapas de una descarga (los valores de Stage, en core/downloader.py)
    "En cola": "Queued",
    "Preparando": "Preparing",
    "Descargando": "Downloading",
    "Convirtiendo": "Converting",
    "Etiquetando": "Tagging",
    "Listo": "Done",
    "Ya la tenías": "You already had it",
    "Error": "Error",
    "Cancelada": "Cancelled",
    # Lo que sale al terminar (ui/workers.py)
    "Con letra": "With lyrics",
    "Sin letra": "No lyrics",
    "Origen {codec} {kbps} kbps": "Source {codec} {kbps} kbps",

    # --- Escuchar antes de descargar (ui/preview_player.py y core/preview.py) ---
    "a tu sistema le falta la librería {libreria}, que el sonido necesita.":
        "your system is missing the {libreria} library, which sound needs.",
    "No se pudo reproducir.": "Couldn't play it.",
    "Esta canción no se puede escuchar desde aquí.": "This song can't be played from here.",

    # --- Ajustes (ui/settings_dialog.py) ---
    "Examinar…": "Browse…",
    "Carpeta de música": "Music folder",
    "Formato": "Format",
    "MP3 V0 (~245 kbps VBR) · recomendado": "MP3 V0 (~245 kbps VBR) · recommended",
    "M4A/AAC original · sin recodificar": "Original M4A/AAC · not re-encoded",
    "Descargas a la vez": "Downloads at once",
    "Igualar el volumen de todas las canciones (-14 LUFS)": "Even out the volume of all songs (-14 LUFS)",
    "No volver a descargar canciones que ya tengo": "Don't download songs I already have again",
    "Álbum": "Album",
    "Buscar el álbum original y la portada del disco": "Find the original album and its cover",
    "Nombre del álbum, año de la primera edición y portada, de MusicBrainz.\n"
    "Si no lo encuentra, se usan los datos del vídeo.":
        "Album name, year of the first release and cover, from MusicBrainz.\n"
        "If it isn't found, the video's details are used.",
    "Letras": "Lyrics",
    "Añadir la letra de cada canción": "Add the lyrics of each song",
    "Va dentro del MP3 o M4A. El iPod la muestra al pulsar el botón central.":
        "It goes inside the MP3 or M4A. The iPod shows it when you press the center button.",
    "Guardar también un archivo .lrc con la letra sincronizada": "Also save a .lrc file with the synced lyrics",
    "Un archivo con la letra y el momento en que se canta cada línea, junto a la canción.\n"
    "Algunos reproductores (Rockbox y muchos MP3) la muestran a la vez que suena.":
        "A file with the lyrics and the moment each line is sung, next to the song.\n"
        "Some players (Rockbox and many MP3 players) show it while the song plays.",
    "Actualizaciones": "Updates",
    "Avisar si hay una versión nueva de tunedrop": "Let me know when there's a new version of tunedrop",
    "Al abrir la app, pregunta a GitHub cuál es la última versión.":
        "When the app opens, it asks GitHub which version is the latest.",
    "Sobre la calidad: YouTube entrega el audio a ~128-160 kbps (Opus o AAC). "
    "MP3 V0 conserva todo lo que hay con un buen tamaño; 320 kbps no añade calidad real. "
    "M4A copia el audio AAC original sin recodificar y el iPod lo lee de forma nativa.\n\n"
    "El álbum y la portada salen de MusicBrainz (musicbrainz.org) y las letras de LRCLIB "
    "(lrclib.net), dos bases de datos gratuitas y abiertas. Si una canción no está, "
    "se descarga igual, con los datos del vídeo.":
        "About quality: YouTube serves audio at ~128-160 kbps (Opus or AAC). "
        "MP3 V0 keeps everything there is at a good size; 320 kbps adds no real quality. "
        "M4A copies the original AAC audio without re-encoding, and the iPod plays it natively.\n\n"
        "The album and cover come from MusicBrainz (musicbrainz.org) and the lyrics from LRCLIB "
        "(lrclib.net), two free and open databases. If a song isn't there, "
        "it's downloaded anyway, with the video's details.",
    "Cancelar": "Cancel",
    "Guardar": "Save",

    # --- Al abrir y al actualizar (ui/startup.py, ui/update_banner.py, core/updates.py) ---
    "Abriendo tunedrop…": "Opening tunedrop…",
    "<b>Hay una versión nueva de tunedrop: {nueva}</b> (tienes la {tuya}).":
        "<b>A new version of tunedrop is out: {nueva}</b> (you have {tuya}).",
    "Actualizar": "Update",
    "Novedades": "What's new",
    "Ocultar hasta la próxima vez": "Hide until next time",
    "Actualizando…": "Updating…",
    "<b>Instalando tunedrop {version}…</b> Puedes seguir usando la app.":
        "<b>Installing tunedrop {version}…</b> You can keep using the app.",
    "<b>tunedrop {version} está instalada.</b> Reinicia la app para usarla.":
        "<b>tunedrop {version} is installed.</b> Restart the app to use it.",
    "Reiniciar": "Restart",
    "<b>No se pudo actualizar.</b> Comprueba tu conexión, o descarga la versión "
    "nueva desde la página de novedades.":
        "<b>Couldn't update.</b> Check your connection, or download the new "
        "version from the What's new page.",
    "Pulsa Intro para cerrar esta ventana": "Press Enter to close this window",
    "Actualízala con «nix profile upgrade tunedrop» o, si está en tu configuración, "
    "con «nix flake update tunedrop» y reconstruyendo el sistema.":
        "Update it with “nix profile upgrade tunedrop” or, if it's in your configuration, "
        "with “nix flake update tunedrop” and rebuilding your system.",
    "Descarga la versión nueva desde la página de novedades.": "Download the new version from the What's new page.",
    "Actualiza el código con «git pull».": "Update the code with “git pull”.",

    # --- Errores (core/) ---
    "Ese enlace no es compatible.": "That link isn't supported.",
    "Ese vídeo es privado.": "That video is private.",
    "Ese vídeo no está disponible.": "That video isn't available.",
    "No se encontró ffmpeg. Ejecuta `{script}` (lo descarga solo) o instálalo con "
    "`{instalar}` y vuelve a abrir tunedrop.":
        "ffmpeg wasn't found. Run `{script}` (it downloads it for you) or install it with "
        "`{instalar}` and open tunedrop again.",
    "yt-dlp no produjo ningún archivo de audio": "yt-dlp didn't produce any audio file",
    # Si una canción no tiene artista o título (core/titles.py y core/paths.py)
    "Desconocido": "Unknown",
    "Sin título": "Untitled",
    "ffmpeg falló sin mensaje": "ffmpeg failed without a message",
}
