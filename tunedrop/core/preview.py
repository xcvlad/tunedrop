"""Escuchar una canción antes de descargarla.

No se descarga nada: yt-dlp consigue la dirección del audio en internet (la
misma que usaría para descargarlo) y el reproductor de Qt lo va reproduciendo
desde ahí, como hace el navegador. Tarda unos 3 segundos en empezar a sonar.

Se pide AAC (m4a) si lo hay, porque lo entiende cualquier reproductor; si no,
el mejor audio que haya. Estas direcciones caducan a las pocas horas, así que
se piden cada vez que se pulsa ▶.
"""

from __future__ import annotations

from ..idioma import tr
from .models import Track
from .runtime import base_ydl_options
from .search import _friendly


class PreviewError(RuntimeError):
    pass


def stream_url(track: Track) -> str:
    """La dirección en internet del audio de la canción, lista para reproducir."""
    import yt_dlp  # se carga aquí para que la ventana aparezca antes (ver ui/startup.py)

    opts = {**base_ydl_options(), "format": "bestaudio[ext=m4a]/bestaudio/best", "noplaylist": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(track.url, download=False)
    except yt_dlp.utils.DownloadError as exc:
        raise PreviewError(_friendly(str(exc))) from exc
    url = (info or {}).get("url")
    if not url:
        raise PreviewError(tr("Esta canción no se puede escuchar desde aquí."))
    return url

