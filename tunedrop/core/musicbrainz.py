"""Datos del álbum y portada original, sacados de MusicBrainz (https://musicbrainz.org).

MusicBrainz es la gran base de datos musical abierta: gratuita, sin registro y
mantenida por su comunidad. De cada canción se busca el ÁLBUM ORIGINAL en el que
salió: nombre, artista del álbum y año de la primera edición. La portada sale de
su archivo de carátulas, Cover Art Archive (https://coverartarchive.org): la del
disco de verdad, cuadrada y nítida, en vez de un fotograma del vídeo.

Cómo se elige, para no equivocarse de disco:
1. Solo discos oficiales que sean álbumes: sin directos, recopilatorios, bandas
   sonoras, remezclas ni maquetas.
2. La grabación tiene que ser la misma canción: mismo título (sin paréntesis) y,
   si se sabe, misma duración (±10 s).
3. Si el título de la canción dice que es un directo o una remezcla, no se busca:
   no se le pondría la portada del álbum de estudio.
4. Un mismo disco tiene muchas ediciones (reediciones, de lujo, vinilo...).
   MusicBrainz las agrupa en un «grupo de publicaciones». Se elige el grupo en
   el que la canción salió antes (después puede aparecer como extra en
   reediciones de otros discos), y el año es el de su primera edición.

El número de pista NO se toma de aquí: cambia de una edición a otra (11 de 24 en
la de lujo, 7 de 9 en el vinilo...) y un número equivocado desordena el álbum.

MusicBrainz solo permite una consulta por segundo desde el mismo ordenador, así
que las consultas de las descargas que van a la vez esperan su turno.
Si no hay conexión o no se encuentra nada, se devuelve None: son extras y nunca
deben estropear una descarga.
"""

from __future__ import annotations

import json
import re
import threading
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass

from .. import __version__

API = "https://musicbrainz.org/ws/2"
PORTADAS = "https://coverartarchive.org"
# MusicBrainz exige que cada programa se identifique con un nombre y un contacto.
USER_AGENT = f"tunedrop/{__version__} (https://github.com/xcvlad/tunedrop)"

MARGEN_SEGUNDOS = 10
# Si el título dice esto, es otra versión de la canción: no se busca el álbum.
_OTRA_VERSION = re.compile(r"\b(live|en vivo|en directo|directo|remix|mix|acoustic|acústic[oa]|"
                           r"unplugged|demo|instrumental|karaoke)\b", re.IGNORECASE)

# Una consulta por segundo como mucho (dejamos un poco de margen).
_turno = threading.Lock()
_ultima_consulta = 0.0
_PAUSA = 1.1


@dataclass
class AlbumInfo:
    album: str
    album_artist: str       # el artista, tal como lo escribe oficialmente (ver apply_album)
    year: str | None        # año de la primera edición del disco
    release_group_id: str   # el «grupo de publicaciones» de MusicBrainz
    title: str = ""         # el título de la canción, tal como lo escribe oficialmente

    @property
    def cover_url(self) -> str:
        """La portada del disco (1200 px; tagger.py la deja en 600)."""
        return f"{PORTADAS}/release-group/{self.release_group_id}/front-1200"


def find_album(artist: str, title: str, duration: float | None = None,
               timeout: float = 10) -> AlbumInfo | None:
    """Busca el álbum original de una canción. None si no está claro cuál es."""
    if not artist or not title or _OTRA_VERSION.search(title):
        return None
    base = (f'recording:"{_limpio(title)}" AND artist:"{_limpio(artist)}" '
            "AND status:official AND primarytype:album")
    # 1.ª consulta: sin excluir recopilatorios. Cada grabación reúne los datos de
    #    todos los discos en los que sale, y las canciones famosas salen en
    #    cientos de recopilatorios: «NOT recopilatorio» dejaría fuera la buena.
    # 2.ª consulta (solo si la 1.ª no da nada): excluyéndolos. De las canciones
    #    muy famosas, MusicBrainz solo devuelve parte de sus discos, y a veces el
    #    álbum no está entre ellos; así aparecen ediciones del álbum menos conocidas.
    # En las dos, los directos, recopilatorios, etc. se descartan disco a disco.
    elegido = None
    for consulta in (base, base + " AND NOT secondarytype:(live OR compilation OR soundtrack OR remix)"):
        datos = _consultar("recording", {"query": consulta, "limit": 50}, timeout)
        if datos is None:
            return None     # MusicBrainz no ha respondido: mejor no adivinar
        elegido = pick_release_group(datos.get("recordings") or [], title, duration)
        if elegido:
            break
    if not elegido:
        return None
    grupo_id, album, album_artist, titulo, anio_grabacion = elegido
    grupo = _consultar(f"release-group/{grupo_id}", {}, timeout)
    if grupo is None:
        return None
    fecha = grupo.get("first-release-date") or ""
    anio = fecha[:4] if re.match(r"\d{4}", fecha) else None
    # Si el álbum salió ANTES que la grabación, esa grabación es un extra que se
    # añadió en una reedición posterior (p. ej. un directo en la edición de lujo):
    # ese no es su álbum.
    if anio and anio_grabacion and anio < anio_grabacion:
        return None
    return AlbumInfo(album=_signos(album), album_artist=_signos(album_artist), year=anio,
                     release_group_id=grupo_id, title=_signos(titulo))


def pick_release_group(recordings: list[dict], title: str,
                       duration: float | None) -> tuple[str, str, str, str, str | None] | None:
    """Entre los resultados de MusicBrainz, el disco original de la canción.

    Devuelve (id del grupo de publicaciones, nombre del álbum, artista, título de
    la canción y año en que salió la grabación elegida).
    """
    buscado = _normalizar(title)
    ediciones: Counter[str] = Counter()
    primera_fecha: dict[str, str] = {}
    datos: dict[str, tuple[str, str, str]] = {}
    anio_grabacion: dict[str, str | None] = {}
    for grabacion in recordings:
        if (grabacion.get("score") or 0) < 80:
            continue                       # MusicBrainz no está seguro de que sea esta
        if _normalizar(grabacion.get("title", "")) != buscado:
            continue                       # otra canción con un título parecido
        if _OTRA_VERSION.search(grabacion.get("title", "")):
            continue                       # «Wonderwall (unplugged)»: otra versión
        largo = grabacion.get("length")
        if duration and largo and abs(largo / 1000 - duration) > MARGEN_SEGUNDOS:
            continue                       # otra versión (más larga o más corta)
        artista = _artista(grabacion)
        for edicion in grabacion.get("releases") or []:
            grupo = edicion.get("release-group") or {}
            if (edicion.get("status") != "Official" or grupo.get("primary-type") != "Album"
                    or grupo.get("secondary-types") or not grupo.get("id")):
                continue
            ediciones[grupo["id"]] += 1
            fecha = edicion.get("date") or "9999"
            primera_fecha[grupo["id"]] = min(fecha, primera_fecha.get(grupo["id"], "9999"))
            datos[grupo["id"]] = (grupo.get("title") or edicion.get("title") or "", artista,
                                  grabacion.get("title") or "")
            estreno = (grabacion.get("first-release-date") or "")[:4]
            if re.fullmatch(r"\d{4}", estreno):
                anio_grabacion[grupo["id"]] = min(estreno, anio_grabacion.get(grupo["id"]) or "9999")
    if not ediciones:
        return None
    # El disco original es aquel en el que la canción salió ANTES: después puede
    # aparecer como extra en reediciones de otros discos (Billie Jean sale en
    # reediciones de «Bad», de 1987, pero es de «Thriller», de 1982). Si hay
    # empate de fecha, el que tiene más ediciones.
    mejor = min(ediciones, key=lambda g: (primera_fecha[g], -ediciones[g]))
    album, artista, titulo = datos[mejor]
    return (mejor, album, artista, titulo, anio_grabacion.get(mejor)) if album else None


def _artista(grabacion: dict) -> str:
    """El nombre del artista tal como lo escribe MusicBrainz («Queen», «ROSALÍA»...)."""
    partes = []
    for credito in grabacion.get("artist-credit") or []:
        partes.append((credito.get("name") or "") + (credito.get("joinphrase") or ""))
    return "".join(partes).strip()


def _signos(texto: str) -> str:
    """Los signos tipográficos de MusicBrainz, como los del teclado: el guion
    especial de «a‐ha» y el apóstrofo curvo de «What’s». Si no, el iPod vería
    «a‐ha» y «a-ha» como dos artistas distintos."""
    # ‐ y ‑: guiones tipográficos; ’: apóstrofo curvo.
    return texto.replace("‐", "-").replace("‑", "-").replace("’", "'")


def _normalizar(texto: str) -> str:
    """Para comparar títulos: sin paréntesis, tildes, mayúsculas ni signos."""
    texto = re.sub(r"[(\[].*?[)\]]", " ", texto)
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", texto.lower()))


def _limpio(texto: str) -> str:
    """Quita lo que rompería la consulta (comillas y barras invertidas)."""
    return re.sub(r'["\\]', " ", texto).strip()


def _consultar(ruta: str, params: dict, timeout: float, intentos: int = 3) -> dict | None:
    """Una consulta a MusicBrainz, respetando el turno de una por segundo.

    Si MusicBrainz está ocupado (responde 503) o tarda demasiado, se reintenta
    un par de veces. None si no hay manera.
    """
    global _ultima_consulta
    url = f"{API}/{ruta}?{urllib.parse.urlencode({**params, 'fmt': 'json'})}"
    for intento in range(intentos):
        with _turno:
            espera = _ultima_consulta + _PAUSA * (1 + intento) - time.monotonic()
            if espera > 0:
                time.sleep(espera)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return json.load(resp)
            except urllib.error.HTTPError as exc:
                if exc.code != 503:
                    return None      # otro error (p. ej. 404): reintentar no sirve
            except Exception:
                pass                 # sin conexión o tarda demasiado: se reintenta
            finally:
                _ultima_consulta = time.monotonic()
    return None
