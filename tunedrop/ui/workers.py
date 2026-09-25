"""Trabajo en segundo plano: búsquedas, miniaturas y descargas, sin congelar la interfaz."""

from __future__ import annotations

import threading
from collections.abc import Callable

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QUrl, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from ..core import search as search_mod
from ..core.downloader import Cancelled, DownloadOptions, Stage, download_track
from ..core.models import Track


class _SearchSignals(QObject):
    finished = Signal(int, list)
    failed = Signal(int, str)


class SearchWorker(QRunnable):
    """Busca o resuelve un enlace. `token` sirve para descartar resultados de búsquedas viejas."""

    def __init__(self, token: int, text: str):
        super().__init__()
        self.token = token
        self.text = text
        self.signals = _SearchSignals()

    def run(self):
        try:
            if search_mod.is_url(self.text):
                tracks = search_mod.resolve(self.text)
            else:
                tracks = search_mod.search(self.text)
            self.signals.finished.emit(self.token, tracks)
        except Exception as exc:  # noqa: BLE001 - cualquier fallo se muestra al usuario
            self.signals.failed.emit(self.token, str(exc))


class ThumbnailLoader(QObject):
    """Descarga miniaturas con la red asíncrona de Qt y las guarda en caché."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._net = QNetworkAccessManager(self)
        self._cache: dict[str, QPixmap] = {}
        self._waiting: dict[str, list[Callable[[QPixmap], None]]] = {}

    def load(self, url: str | None, callback: Callable[[QPixmap], None]) -> None:
        if not url:
            return
        if url in self._cache:
            callback(self._cache[url])
            return
        if url in self._waiting:
            self._waiting[url].append(callback)
            return
        self._waiting[url] = [callback]
        reply = self._net.get(QNetworkRequest(QUrl(url)))
        reply.finished.connect(lambda r=reply, u=url: self._done(r, u))

    def _done(self, reply: QNetworkReply, url: str) -> None:
        callbacks = self._waiting.pop(url, [])
        pix = QPixmap()
        if reply.error() == QNetworkReply.NoError:
            pix.loadFromData(reply.readAll())
        reply.deleteLater()
        if pix.isNull():
            return
        self._cache[url] = pix
        for cb in callbacks:
            try:
                cb(pix)
            except RuntimeError:
                pass  # el widget se destruyó mientras cargaba


class _DownloadSignals(QObject):
    progress = Signal(str, str, float, str)   # id, etapa, fracción, extra
    finished = Signal(str, str, str)          # id, ruta, info de calidad
    failed = Signal(str, str)                 # id, mensaje
    cancelled = Signal(str)


class _DownloadJob(QRunnable):
    def __init__(self, key: str, track: Track, options: DownloadOptions,
                 signals: _DownloadSignals, cancel: threading.Event):
        super().__init__()
        self.key, self.track, self.options = key, track, options
        self.signals, self.cancel = signals, cancel

    def run(self):
        if self.cancel.is_set():
            self.signals.cancelled.emit(self.key)
            return
        try:
            result = download_track(
                self.track, self.options,
                lambda stage, frac, extra: self.signals.progress.emit(
                    self.key, stage.value, frac, extra),
                self.cancel,
            )
            quality = ""
            if result.source_bitrate:
                codec = (result.source_codec or "").split(".")[0].replace("mp4a", "AAC").upper()
                quality = f"Origen {codec} {round(result.source_bitrate)} kbps"
            self.signals.finished.emit(self.key, str(result.path), quality)
        except Cancelled:
            self.signals.cancelled.emit(self.key)
        except Exception as exc:  # noqa: BLE001
            self.signals.failed.emit(self.key, str(exc).splitlines()[0][:300])


class DownloadManager(QObject):
    """Cola de descargas en paralelo con cancelación individual."""

    progress = Signal(str, str, float, str)
    finished = Signal(str, str, str)
    failed = Signal(str, str)
    cancelled = Signal(str)

    def __init__(self, concurrent: int = 3, parent=None):
        super().__init__(parent)
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(concurrent)
        self._cancels: dict[str, threading.Event] = {}
        self._signals = _DownloadSignals()
        self._signals.progress.connect(self.progress)
        self._signals.finished.connect(self._on_finished)
        self._signals.failed.connect(self._on_failed)
        self._signals.cancelled.connect(self._on_cancelled)

    def set_concurrency(self, n: int) -> None:
        self._pool.setMaxThreadCount(max(1, n))

    def is_active(self, key: str) -> bool:
        return key in self._cancels

    @property
    def active_count(self) -> int:
        return len(self._cancels)

    def enqueue(self, key: str, track: Track, options: DownloadOptions) -> None:
        if key in self._cancels:
            return
        cancel = threading.Event()
        self._cancels[key] = cancel
        self.progress.emit(key, Stage.QUEUED.value, 0.0, "")
        self._pool.start(_DownloadJob(key, track, options, self._signals, cancel))

    def cancel(self, key: str) -> None:
        if key in self._cancels:
            self._cancels[key].set()

    def cancel_all(self) -> None:
        for ev in self._cancels.values():
            ev.set()

    def wait(self, msecs: int = 5000) -> None:
        self._pool.waitForDone(msecs)

    def _on_finished(self, key: str, path: str, quality: str):
        self._cancels.pop(key, None)
        self.finished.emit(key, path, quality)

    def _on_failed(self, key: str, message: str):
        self._cancels.pop(key, None)
        self.failed.emit(key, message)

    def _on_cancelled(self, key: str):
        self._cancels.pop(key, None)
        self.cancelled.emit(key)


def start_search(pool: QThreadPool, token: int, text: str,
                 on_done: Callable[[int, list], None], on_error: Callable[[int, str], None]):
    worker = SearchWorker(token, text)
    worker.signals.finished.connect(on_done)
    worker.signals.failed.connect(on_error)
    pool.start(worker)
    return worker

