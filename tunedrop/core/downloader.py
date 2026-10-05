"""Descarga completa de una canción: audio, conversión, etiquetas, álbum, carátula y letra, en la carpeta de música."""

from __future__ import annotations

import shutil
import tempfile
import threading
import unicodedata
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from ..idioma import tr
from .converter import convert
from .lyrics import Lyrics, find_lyrics
from .musicbrainz import AlbumInfo, find_album
from .models import AudioFormat, Track
from .paths import build_output_path, unique_path
from .runtime import base_ydl_options
from .tagger import Tags, fetch_image, prepare_cover, write_tags
from .titles import clean_channel, clean_title, soften_caps, split_artist_title


class Stage(str, Enum):
    QUEUED = "En cola"
    FETCHING = "Preparando"
    DOWNLOADING = "Descargando"
    CONVERTING = "Convirtiendo"
    TAGGING = "Etiquetando"
    DONE = "Listo"
    SKIPPED = "Ya la tenías"
    FAILED = "Error"
    CANCELLED = "Cancelada"


# (etapa, progreso 0-1, texto extra)
ProgressCallback = Callable[[Stage, float, str], None]


class Cancelled(Exception):
    pass


@dataclass
class DownloadOptions:
    output_dir: Path
    audio_format: AudioFormat
    normalize: bool = False
    lyrics: bool = True       # buscar la letra y guardarla dentro de la canción
    lrc_file: bool = False    # guardar además un .lrc con la letra sincronizada
    album_info: bool = True   # buscar el álbum original y su portada (musicbrainz.py)


@dataclass
class DownloadResult:
    path: Path
    source_bitrate: float | None  # kbps reales del audio original
    source_codec: str | None
    lyrics: Lyrics | None = None  # la letra encontrada (None si no hay o está desactivado)
    album: AlbumInfo | None = None  # el álbum original encontrado (ídem)


def audio_selector(fmt: AudioFormat) -> str:
    if fmt is AudioFormat.M4A:
        # AAC original para copiarlo sin pérdidas; si no hay, el mejor audio y se recodifica.
        return "bestaudio[ext=m4a]/bestaudio/best"
    return "bestaudio/best"


def download_track(
    track: Track,
    options: DownloadOptions,
    progress: ProgressCallback,
    cancel_event: threading.Event | None = None,
) -> DownloadResult:
    import yt_dlp  # se carga aquí y no arriba para que la ventana aparezca antes (ver ui/startup.py)

    cancel_event = cancel_event or threading.Event()

    def check_cancel():
        if cancel_event.is_set():
            raise Cancelled()

    def hook(d: dict):
        check_cancel()
        if d.get("status") == "downloading":
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes") or 0
            speed = d.get("speed")
            extra = f"{speed / 1_048_576:.1f} MB/s" if speed else ""
            progress(Stage.DOWNLOADING, done / total if total else 0.0, extra)

    progress(Stage.FETCHING, 0.0, "")
    workdir = Path(tempfile.mkdtemp(prefix="tunedrop-"))
    try:
        ydl_opts = {
            **base_ydl_options(),
            "format": audio_selector(options.audio_format),
            "outtmpl": str(workdir / "audio.%(ext)s"),
            "progress_hooks": [hook],
            "noplaylist": True,
            "writethumbnail": False,
        }
        busqueda_letra = busqueda_album = None
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # 1. Qué canción es (título, artista, duración...), sin descargar nada.
                info = ydl.extract_info(track.url, download=False)
                tags = build_tags(info, track)
                # La letra y el álbum se buscan ya, en otros hilos, mientras se
                # descarga y se convierte el audio: así casi nunca hay que esperarlos.
                # Se buscan con el primer artista (no «A, B»), que es como están
                # en LRCLIB y en MusicBrainz.
                artista, duracion = tags.album_artist or tags.artist, info.get("duration")
                if options.lyrics:
                    busqueda_letra = _en_segundo_plano(find_lyrics, artista, tags.title, duracion)
                if options.album_info:
                    busqueda_album = _en_segundo_plano(_album_y_portada, artista, tags.title, duracion)
                # 2. Descargar el audio (es lo que extract_info(download=True) hace después).
                info = ydl.process_ie_result(info, download=True)
        except yt_dlp.utils.DownloadError as exc:
            if cancel_event.is_set():
                raise Cancelled() from exc
            raise RuntimeError(str(exc).replace("ERROR: ", "")) from exc
        check_cancel()

        downloaded = next((p for p in workdir.iterdir() if p.stem == "audio"), None)
        if not downloaded:
            raise RuntimeError(tr("yt-dlp no produjo ningún archivo de audio"))

        fmt = options.audio_format
        progress(Stage.CONVERTING, 1.0, "")
        temp_out = workdir / f"out.{fmt.extension}"
        convert(downloaded, temp_out, fmt, options.normalize,
                source_is_aac=str(info.get("acodec", "")).startswith("mp4a"))
        check_cancel()

        progress(Stage.TAGGING, 1.0, "")
        lyrics = _resultado(busqueda_letra)
        if lyrics:
            tags.lyrics = lyrics.plain
        album, cover = _resultado(busqueda_album) or (None, None)
        if album:
            apply_album(tags, album)
        # La portada del disco si la hay; si no, la miniatura del vídeo.
        cover = cover or _best_cover(info)
        write_tags(temp_out, tags, cover)

        # El nombre del archivo se decide al final, con el artista y el título ya
        # corregidos (p. ej. «BAD BUNNY» -> «Bad Bunny» gracias a MusicBrainz).
        target = unique_path(build_output_path(
            options.output_dir,
            artist=tags.album_artist or tags.artist, title=tags.title,
            extension=options.audio_format.extension,
        ))
        save_to_destination(temp_out, target)
        if lyrics and lyrics.synced and options.lrc_file:
            save_lrc(target, tags, lyrics.synced)
        progress(Stage.DONE, 1.0, "")
        return DownloadResult(target, info.get("abr"), info.get("acodec"), lyrics, album)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def save_to_destination(temp_file: Path, target: Path) -> None:
    """Deja la canción terminada en la carpeta de música.

    Se COPIA (y la temporal se borra después) en vez de moverla. En Windows, mover un
    archivo conserva sus permisos, y la carpeta temporal de Python (mkdtemp) es privada:
    la canción llegaba a Música sin tu usuario en los permisos, y en algunos PC pedía
    permisos de administrador para abrirla. Un archivo copiado es nuevo y hereda los
    permisos normales de la carpeta de destino.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copyfile(temp_file, target)
    except BaseException:
        target.unlink(missing_ok=True)  # no dejar una canción a medias
        raise


def _en_segundo_plano(funcion, *args) -> Future:
    """Ejecuta una función en otro hilo; su resultado se recoge luego con _resultado."""
    hilo = ThreadPoolExecutor(max_workers=1)
    futuro = hilo.submit(funcion, *args)
    hilo.shutdown(wait=False)   # el hilo se cierra solo al terminar
    return futuro


def _resultado(futuro: Future | None):
    """El resultado de _en_segundo_plano, o None si falló: la letra y el álbum son
    extras y nunca deben estropear la descarga."""
    if futuro is None:
        return None
    try:
        return futuro.result()
    except Exception:
        return None


def _album_y_portada(artist: str, title: str, duration: float | None) -> tuple[AlbumInfo, bytes | None] | None:
    """El álbum original (musicbrainz.py) y su portada, ya preparada para el iPod."""
    album = find_album(artist, title, duration)
    if not album:
        return None
    portada = None
    datos = fetch_image(album.cover_url, timeout=20)
    if datos:
        try:
            portada = prepare_cover(datos)
        except Exception:
            portada = None        # imagen rota: se usará la miniatura del vídeo
    return album, portada


def apply_album(tags: Tags, album: AlbumInfo) -> None:
    """Pone en las etiquetas el álbum original y su año.

    Además, el artista y el título pasan a escribirse como en MusicBrainz, pero
    SOLO si son las mismas palabras y cambian las mayúsculas o las tildes
    («BAD BUNNY» -> «Bad Bunny», «Titi Me Pregunto» -> «Tití Me Preguntó»). Así
    todas las canciones de un artista llevan su nombre escrito igual y el iPod no
    lo separa en dos. Nunca se quita ni se añade nada («(feat. X)» se queda).
    """
    if tags.album and tags.album.casefold() != album.album.casefold():
        # YouTube Music daba otro disco (p. ej. un recopilatorio): su número de
        # pista era de ese disco, no de este.
        tags.track_number = None
    tags.album = album.album
    if album.year:
        tags.year = album.year
    if album.title and _misma_escritura(tags.title, album.title):
        tags.title = album.title
    if _misma_escritura(tags.artist, album.album_artist):
        tags.artist = album.album_artist
    if tags.album_artist and _misma_escritura(tags.album_artist, album.album_artist):
        tags.album_artist = album.album_artist


def _misma_escritura(a: str, b: str) -> bool:
    """True si a y b son lo mismo salvo mayúsculas y tildes («TITI» y «Tití»)."""
    def clave(texto: str) -> str:
        sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
        return " ".join(sin_tildes.casefold().split())
    return bool(a) and bool(b) and clave(a) == clave(b)


def save_lrc(song: Path, tags: Tags, synced: str) -> Path:
    """Guarda la letra sincronizada en un .lrc junto a la canción y con su mismo nombre.

    Los reproductores que entienden .lrc (Rockbox, muchos MP3 baratos...) lo buscan
    así: «Artista - Título.lrc» al lado de «Artista - Título.mp3». Las primeras
    líneas ([ar:], [ti:], [al:]) dicen de qué canción es.
    """
    cabecera = [f"[ar:{tags.artist}]", f"[ti:{tags.title}]"]
    if tags.album:
        cabecera.append(f"[al:{tags.album}]")
    lrc = song.with_suffix(".lrc")
    # UTF-8 con BOM (utf-8-sig): la marca del principio ayuda a los reproductores
    # antiguos a mostrar bien las tildes y la ñ.
    lrc.write_text("\n".join([*cabecera, synced]) + "\n", encoding="utf-8-sig")
    return lrc


def build_tags(info: dict, track: Track) -> Tags:
    """Prefiere los metadatos musicales de YouTube Music; si no hay, los saca del título."""
    artists = info.get("artists") or ([info["artist"]] if info.get("artist") else None)
    song = info.get("track")
    if artists and song:
        artist = ", ".join(dict.fromkeys(artists))
        # También puede traer relleno, como «Canción (Remastered 2011)».
        title = clean_title(song) or song
    else:
        artist, title = split_artist_title(info.get("title") or track.title,
                                           info.get("channel") or track.channel)
    album_artist = info.get("album_artist") or (artists[0] if artists else artist)
    year = info.get("release_year") or info.get("release_date") or info.get("upload_date")
    # «BAD BUNNY» -> «Bad Bunny» (ver soften_caps). Si MusicBrainz encuentra la
    # canción, apply_album pone además cómo la escribe el artista oficialmente.
    return Tags(
        title=soften_caps(title.strip()),
        artist=soften_caps(artist.strip()),
        album=info.get("album") or None,
        album_artist=soften_caps(clean_channel(album_artist) or artist.strip()),
        track_number=info.get("track_number"),
        year=str(year)[:4] if year else None,
        comment=info.get("webpage_url") or track.url,
    )


def _best_cover(info: dict, intentos: int = 10) -> bytes | None:
    """La miniatura del vídeo, como portada de reserva.

    yt-dlp lista muchas miniaturas posibles, pero no todas existen: los vídeos
    antiguos no tienen las más grandes (maxresdefault, hq720) y dan error 404, que
    a veces tarda más de un segundo en llegar. Por eso se piden todas A LA VEZ y se
    elige la mejor que exista (una detrás de otra se iban casi 5 segundos).
    Pillow lee también .webp.
    """
    thumbs = [t for t in info.get("thumbnails") or [] if t.get("url")]
    # yt-dlp las ordena de peor a mejor según su preferencia.
    thumbs.sort(key=lambda t: (t.get("preference") or 0, t.get("width") or 0))
    candidatas = list(reversed(thumbs))[:intentos]
    if not candidatas:
        return None
    with ThreadPoolExecutor(max_workers=len(candidatas)) as hilos:
        imagenes = list(hilos.map(lambda t: fetch_image(t["url"]), candidatas))
    for data in imagenes:          # en orden, de la mejor a la peor
        if data:
            try:
                return prepare_cover(data)
            except Exception:
                continue
    return None

