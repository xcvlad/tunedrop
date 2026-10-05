"""Reproductor para escuchar una canción antes de descargarla.

Solo suena una canción a la vez. Al pulsar ▶:
1. «cargando»: en otro hilo, yt-dlp consigue la dirección del audio (core/preview.py).
2. «sonando»: el reproductor de Qt (QMediaPlayer) la reproduce desde internet.
3. «parado»: al pulsar ■, al acabar la canción, al escuchar otra o al cerrar la app.
Si algo falla, «error» con el motivo.

El módulo de sonido de Qt (QtMultimedia) se carga la primera vez que se pulsa ▶,
no al abrir la app, para que la ventana siga apareciendo rápido.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QUrl, Signal

from ..core.models import Track
from ..core.preview import stream_url
from ..idioma import tr

CARGANDO, SONANDO, PARADO, ERROR = "cargando", "sonando", "parado", "error"


class _Signals(QObject):
    done = Signal(object)


class _UrlTask(QRunnable):
    """Pide la dirección del audio en otro hilo, para que la ventana no se congele."""

    def __init__(self, track: Track, on_done):
        super().__init__()
        self.track = track
        self.signals = _Signals()
        self.signals.done.connect(on_done)

    def run(self):
        try:
            result = stream_url(self.track)
        except Exception as exc:  # noqa: BLE001 - el motivo se muestra en la tarjeta
            result = exc
        self.signals.done.emit(result)


class PreviewPlayer(QObject):
    state_changed = Signal(str, str, str)   # canción (clave), estado, mensaje de error
    progress = Signal(str, int, int)        # canción (clave), posición y duración en ms

    def __init__(self, parent=None):
        super().__init__(parent)
        self.key: str | None = None   # la canción que suena (o se está cargando)
        self.state = PARADO
        self._token = 0               # para ignorar respuestas de canciones anteriores
        self._player = None
        self._tasks: list[_UrlTask] = []

    def toggle(self, key: str, track: Track) -> None:
        """▶ en una canción: si ya es la que suena, la para; si no, la reproduce."""
        if key == self.key and self.state in (CARGANDO, SONANDO):
            self.stop()
        else:
            self.play(key, track)

    def play(self, key: str, track: Track) -> None:
        self.stop()
        self._token += 1
        token = self._token
        self.key = key
        self._set_state(CARGANDO)
        task = _UrlTask(track, lambda result: self._on_url(task, token, result))
        self._tasks.append(task)   # para que Python no la borre mientras trabaja
        QThreadPool.globalInstance().start(task)

    def stop(self) -> None:
        if self.key is None:
            return
        key, self.key = self.key, None   # sin canción: el «posición 0» del stop se ignora
        self._token += 1                 # si aún estaba cargando, su respuesta se ignorará
        if self._player is not None:
            self._player.stop()
            self._player.setSource(QUrl())
        self._set_state(PARADO, key=key)

    # --- lo de dentro ---------------------------------------------------------

    def _on_url(self, task: _UrlTask, token: int, result) -> None:
        if task in self._tasks:
            self._tasks.remove(task)
        if token != self._token:
            return                # mientras cargaba, se pulsó otra canción o ■
        if isinstance(result, Exception):
            self._set_state(ERROR, str(result).splitlines()[0][:200])
            self.key = None
            return
        try:
            player = self._ensure_player()
        except ImportError as exc:
            # En Linux, el sonido de Qt necesita algunas librerías del sistema
            # (sobre todo libpulse). El mensaje dice cuál falta: «libpulse.so.0: ...».
            falta = str(exc).split(":")[0]
            self._set_state(ERROR, tr("a tu sistema le falta la librería {libreria}, que el sonido necesita.", libreria=falta))
            self.key = None
            return
        player.setSource(QUrl(result))
        player.play()

    def _ensure_player(self):
        if self._player is None:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

            self._player = QMediaPlayer(self)
            self._output = QAudioOutput(self)
            self._output.setVolume(0.8)
            self._player.setAudioOutput(self._output)
            self._player.positionChanged.connect(self._on_position)
            self._player.mediaStatusChanged.connect(self._on_status)
            self._player.errorOccurred.connect(self._on_error)
        return self._player

    def _on_position(self, position: int) -> None:
        if self.key is None:
            return
        if self.state == CARGANDO and position > 0:
            self._set_state(SONANDO)      # ya se oye de verdad
        self.progress.emit(self.key, position, self._player.duration())

    def _on_status(self, status) -> None:
        from PySide6.QtMultimedia import QMediaPlayer

        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.stop()

    def _on_error(self, error, message: str) -> None:
        if self.key is not None:
            self._player.stop()
            self._set_state(ERROR, message or tr("No se pudo reproducir."))
            self.key = None

    def _set_state(self, state: str, message: str = "", key: str | None = None) -> None:
        self.state = state
        key = key or self.key
        if key is not None:
            self.state_changed.emit(key, state, message)
