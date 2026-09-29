"""Etiquetas y carátula compatibles con iPods y reproductores MP3 antiguos."""

from __future__ import annotations

import io
import ssl
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from mutagen.id3 import APIC, COMM, ID3, TALB, TDRC, TIT2, TPE1, TPE2, TRCK, USLT, ID3NoHeaderError
from mutagen.mp4 import MP4, MP4Cover
from PIL import Image

COVER_SIZE = 600  # los iPods clásicos muestran bien hasta ~600 px


@dataclass
class Tags:
    title: str
    artist: str
    album: str | None = None
    album_artist: str | None = None
    track_number: int | None = None
    year: str | None = None
    comment: str | None = None
    lyrics: str | None = None  # letra normal (ver lyrics.py); el iPod la muestra


def _contexto_ssl() -> ssl.SSLContext:
    """Comprobación normal de certificados (válido, de quien dice ser, sin caducar),
    pero sin la regla extra «estricta» que Python aplica desde la 3.13.

    Algunos servidores de archive.org, de donde salen las portadas de los discos,
    tienen un certificado que no cumple un detalle de esa regla y Python 3.13+
    rechazaría la conexión. curl y los navegadores no aplican esa regla.
    """
    contexto = ssl.create_default_context()
    contexto.verify_flags &= ~getattr(ssl, "VERIFY_X509_STRICT", 0)
    return contexto


def fetch_image(url: str, timeout: float = 15) -> bytes | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=_contexto_ssl()) as resp:
            return resp.read()
    except Exception:
        return None


def prepare_cover(data: bytes) -> bytes:
    """Recorta al centro en cuadrado, lo reduce y lo guarda como JPEG baseline.

    Los iPods clásicos no muestran JPEG progresivos, y las miniaturas de YouTube son 16:9.
    """
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img = _trim_letterbox(img)
    side = min(img.size)
    left = (img.width - side) // 2
    top = (img.height - side) // 2
    img = img.crop((left, top, left + side, top + side))
    if side > COVER_SIZE:
        img = img.resize((COVER_SIZE, COVER_SIZE), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, "JPEG", quality=90, progressive=False, optimize=True)
    return out.getvalue()


def _trim_letterbox(img: Image.Image, threshold: int = 16) -> Image.Image:
    """Quita las franjas negras laterales o superiores (típicas de los vídeos «Topic» con portada)."""
    gray = img.convert("L").point(lambda p: 255 if p > threshold else 0)
    box = gray.getbbox()
    if not box:
        return img
    w, h = box[2] - box[0], box[3] - box[1]
    # Recorta solo si el contenido es claramente más pequeño que la imagen.
    if w * h < img.width * img.height * 0.9 and w > 50 and h > 50:
        return img.crop(box)
    return img


def write_tags(path: Path, tags: Tags, cover: bytes | None) -> None:
    if path.suffix.lower() == ".mp3":
        _write_id3(path, tags, cover)
    elif path.suffix.lower() in (".m4a", ".mp4"):
        _write_mp4(path, tags, cover)
    else:
        raise ValueError(f"Formato no soportado para etiquetas: {path.suffix}")


def _write_id3(path: Path, tags: Tags, cover: bytes | None) -> None:
    try:
        id3 = ID3(path)
        id3.delete(path)
    except ID3NoHeaderError:
        pass
    id3 = ID3()
    id3.add(TIT2(encoding=1, text=tags.title))
    id3.add(TPE1(encoding=1, text=tags.artist))
    id3.add(TPE2(encoding=1, text=tags.album_artist or tags.artist))
    if tags.album:
        id3.add(TALB(encoding=1, text=tags.album))
    if tags.track_number:
        id3.add(TRCK(encoding=1, text=str(tags.track_number)))
    if tags.year:
        id3.add(TDRC(encoding=1, text=tags.year))
    if tags.comment:
        id3.add(COMM(encoding=1, lang="eng", desc="", text=tags.comment))
    if tags.lyrics:
        # USLT es la etiqueta de la letra. Idioma «eng», como hace iTunes: el iPod no lo usa.
        id3.add(USLT(encoding=1, lang="eng", desc="", text=tags.lyrics))
    if cover:
        id3.add(APIC(encoding=0, mime="image/jpeg", type=3, desc="Cover", data=cover))
    # ID3v2.3 con UTF-16 (encoding=1): lo que mejor leen iPods y reproductores antiguos.
    id3.save(path, v2_version=3)


def _write_mp4(path: Path, tags: Tags, cover: bytes | None) -> None:
    mp4 = MP4(path)
    mp4.delete()
    mp4["\xa9nam"] = [tags.title]
    mp4["\xa9ART"] = [tags.artist]
    mp4["aART"] = [tags.album_artist or tags.artist]
    if tags.album:
        mp4["\xa9alb"] = [tags.album]
    if tags.track_number:
        mp4["trkn"] = [(tags.track_number, 0)]
    if tags.year:
        mp4["\xa9day"] = [tags.year]
    if tags.comment:
        mp4["\xa9cmt"] = [tags.comment]
    if tags.lyrics:
        mp4["\xa9lyr"] = [tags.lyrics]
    if cover:
        mp4["covr"] = [MP4Cover(cover, imageformat=MP4Cover.FORMAT_JPEG)]
    mp4.save()
