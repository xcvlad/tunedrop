"""Tarjetas de resultado y de la lista de descarga."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QProgressBar, QPushButton, QSizePolicy, QVBoxLayout, QWidget,
)

from ..core.downloader import Stage
from ..core.models import Track
from . import icons, theme


def rounded_cover(src: QPixmap, w: int, h: int, radius: int = 8) -> QPixmap:
    """Escala recortando para rellenar w×h, con esquinas redondeadas y nítido en HiDPI."""
    ratio = 2
    scaled = src.scaled(w * ratio, h * ratio, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = (scaled.width() - w * ratio) // 2
    y = (scaled.height() - h * ratio) // 2
    out = QPixmap(w * ratio, h * ratio)
    out.fill(Qt.transparent)
    painter = QPainter(out)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, w * ratio, h * ratio, radius * ratio, radius * ratio)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, scaled, x, y, w * ratio, h * ratio)
    painter.end()
    out.setDevicePixelRatio(ratio)
    return out


def placeholder_cover(w: int, h: int) -> QPixmap:
    ratio = 2
    pix = QPixmap(w * ratio, h * ratio)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addRoundedRect(0, 0, w * ratio, h * ratio, 8 * ratio, 8 * ratio)
    painter.fillPath(path, QColor(theme.CARD_HOVER))
    note = icons.pixmap("music", min(w, h) // 2, theme.MUTED)
    nw = note.width()
    painter.drawPixmap((w * ratio - nw) // 2, (h * ratio - nw) // 2, note)
    painter.end()
    pix.setDevicePixelRatio(ratio)
    return pix


def _elide(label: QLabel, text: str) -> None:
    label.setText(text)
    label.setToolTip(text)
    label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)


def _mm_ss(ms: int) -> str:
    s = max(ms, 0) // 1000
    return f"{s // 60}:{s % 60:02d}"


class ResultCard(QWidget):
    """Una canción encontrada, con botón para añadirla o quitarla de la lista,
    y un botón ▶ encima de la miniatura para escucharla antes (ui/preview_player.py)."""

    toggled = Signal(object)         # Track: añadir o quitar de la lista
    play_requested = Signal(object)  # Track: ▶ o ■

    COVER = QSize(112, 63)
    PLAY = 30   # tamaño del botón ▶

    def __init__(self, track: Track, parent=None):
        super().__init__(parent)
        self.track = track
        self.setObjectName("Card")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)

        self.cover = QLabel()
        self.cover.setFixedSize(self.COVER)
        self.cover.setPixmap(placeholder_cover(self.COVER.width(), self.COVER.height()))

        # Escuchar: botón redondo en el centro de la miniatura y, mientras suena,
        # una barrita de progreso en su borde de abajo.
        self.play = QPushButton(self.cover)
        self.play.setObjectName("Play")
        self.play.setCursor(Qt.PointingHandCursor)
        self.play.setFixedSize(self.PLAY, self.PLAY)
        self.play.move((self.COVER.width() - self.PLAY) // 2, (self.COVER.height() - self.PLAY) // 2)
        self.play.clicked.connect(lambda: self.play_requested.emit(self.track))
        self.play_bar = QProgressBar(self.cover)
        self.play_bar.setObjectName("PlayBar")
        self.play_bar.setRange(0, 1000)
        self.play_bar.setTextVisible(False)
        self.play_bar.setGeometry(6, self.COVER.height() - 7, self.COVER.width() - 12, 3)
        self.play_bar.hide()
        # La ruedita de «cargando» es el icono girando un poco cada 50 ms.
        self._spin_timer = QTimer(self, interval=50, timeout=self._spin)
        self._angle = 0

        self.title = QLabel()
        self.title.setObjectName("CardTitle")
        _elide(self.title, track.title)
        meta = " · ".join(x for x in (track.channel, track.duration_text) if x)
        self._meta_text = meta
        self.meta = QLabel(meta)
        self.meta.setObjectName("Muted")
        self.badge = QLabel("Ya descargada")
        self.badge.setObjectName("Badge")
        self.badge.hide()

        text = QVBoxLayout()
        text.setSpacing(3)
        text.addStretch()
        text.addWidget(self.title)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self.meta)
        row.addWidget(self.badge)
        row.addStretch()
        text.addLayout(row)
        text.addStretch()

        self.button = QPushButton()
        self.button.setObjectName("Add")
        self.button.setCursor(Qt.PointingHandCursor)
        self.button.clicked.connect(lambda: self.toggled.emit(self.track))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 14, 10)
        layout.setSpacing(14)
        layout.addWidget(self.cover)
        layout.addLayout(text, 1)
        layout.addWidget(self.button)
        self.set_added(False)
        self.set_preview_state("parado")

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggled.emit(self.track)
        super().mouseReleaseEvent(event)

    def set_cover(self, pix: QPixmap) -> None:
        self.cover.setPixmap(rounded_cover(pix, self.COVER.width(), self.COVER.height()))

    def set_added(self, added: bool) -> None:
        self.button.setProperty("added", added)
        self.button.setIcon(icons.icon("check" if added else "plus", 18, "#ffffff" if added else theme.TEXT, 2.4))
        self.button.setToolTip("Quitar de la lista" if added else "Añadir a la lista")
        self.button.style().unpolish(self.button)
        self.button.style().polish(self.button)

    def set_downloaded(self, downloaded: bool) -> None:
        self.badge.setVisible(downloaded)

    # --- Escuchar antes de descargar ---------------------------------------------

    def set_preview_state(self, state: str) -> None:
        """«cargando», «sonando», «parado» o «error» (ver ui/preview_player.py)."""
        self._spin_timer.stop()
        self.play.setProperty("playing", state in ("cargando", "sonando"))
        self.play.style().unpolish(self.play)
        self.play.style().polish(self.play)
        if state == "cargando":
            self.play.setToolTip("Cargando… (pulsa para cancelar)")
            self._spin_timer.start()
            self._spin()
            self.meta.setText(f"Cargando…  ·  {self._meta_text}")
        elif state == "sonando":
            self.play.setIcon(icons.icon("stop", 16, "#ffffff"))
            self.play.setToolTip("Parar")
            self.play_bar.show()
        else:
            self.play.setIcon(icons.icon("play", 16, "#ffffff"))
            self.play.setToolTip("Escuchar")
            self.play_bar.hide()
            self.play_bar.setValue(0)
            self.meta.setStyleSheet("")
            self.meta.setText(self._meta_text)

    def set_preview_progress(self, position: int, duration: int) -> None:
        if duration > 0:
            self.play_bar.setValue(int(position * 1000 / duration))
        self.meta.setStyleSheet(f"color: {theme.ACCENT_2};")
        self.meta.setText(f"♪ {_mm_ss(position)} / {_mm_ss(duration)}  ·  {self.track.channel}")

    def _spin(self) -> None:
        self._angle = (self._angle + 30) % 360
        self.play.setIcon(QIcon(_rotated(icons.pixmap("loader", 16, "#ffffff", 2.6), self._angle)))


def _rotated(pix: QPixmap, angle: float) -> QPixmap:
    """El mismo icono girado, sin que cambie de tamaño (para la ruedita)."""
    ratio = pix.devicePixelRatio()
    out = QPixmap(pix.size())
    out.setDevicePixelRatio(ratio)
    out.fill(Qt.transparent)
    lado = pix.width() / ratio
    painter = QPainter(out)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.translate(lado / 2, lado / 2)
    painter.rotate(angle)
    painter.drawPixmap(QPointF(-lado / 2, -lado / 2), pix)
    painter.end()
    return out


class QueueCard(QWidget):
    """Una canción de la lista de descarga, con su progreso y acciones."""

    remove_requested = Signal(str)
    retry_requested = Signal(str)
    open_requested = Signal(str)

    COVER = QSize(48, 48)

    def __init__(self, key: str, track: Track, parent=None):
        super().__init__(parent)
        self.key = key
        self.track = track
        self.stage: Stage | None = None
        self.path: str | None = None
        self.setObjectName("Card")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.cover = QLabel()
        self.cover.setFixedSize(self.COVER)
        self.cover.setPixmap(placeholder_cover(self.COVER.width(), self.COVER.height()))

        self.title = QLabel()
        self.title.setObjectName("CardTitle")
        _elide(self.title, track.title)
        self.status = QLabel()
        self.status.setObjectName("Muted")
        self.status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setTextVisible(False)
        self.bar.hide()

        text = QVBoxLayout()
        text.setSpacing(4)
        text.addWidget(self.title)
        text.addWidget(self.status)
        text.addWidget(self.bar)

        self.action = QPushButton()
        self.action.setObjectName("Icon")
        self.action.setCursor(Qt.PointingHandCursor)
        self.action.clicked.connect(self._on_action)
        self.remove = QPushButton()
        self.remove.setObjectName("Icon")
        self.remove.setCursor(Qt.PointingHandCursor)
        self.remove.setIcon(icons.icon("x", 16, theme.MUTED))
        self.remove.setToolTip("Quitar")
        self.remove.clicked.connect(lambda: self.remove_requested.emit(self.key))

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 8, 8)
        layout.setSpacing(12)
        layout.addWidget(self.cover)
        layout.addLayout(text, 1)
        layout.addWidget(self.action)
        layout.addWidget(self.remove)
        self.set_pending()

    def set_cover(self, pix: QPixmap) -> None:
        self.cover.setPixmap(rounded_cover(pix, self.COVER.width(), self.COVER.height()))

    # --- estados -------------------------------------------------------------

    def set_pending(self) -> None:
        self.stage = None
        self.status.setText(" · ".join(x for x in (self.track.channel, self.track.duration_text) if x))
        self.status.setStyleSheet("")
        self.bar.hide()
        self.action.hide()

    def set_progress(self, stage: Stage, fraction: float, extra: str) -> None:
        self.stage = stage
        self.bar.show()
        self.bar.setProperty("state", "")
        self._repolish(self.bar)
        if stage is Stage.DOWNLOADING:
            self.bar.setRange(0, 1000)
            self.bar.setValue(int(fraction * 1000))
            pct = f"{fraction * 100:.0f} %"
            self.status.setText(f"{stage.value} · {pct}" + (f" · {extra}" if extra else ""))
        else:
            # Etapas sin porcentaje: barra animada indeterminada.
            if stage in (Stage.QUEUED,):
                self.bar.setRange(0, 1000)
                self.bar.setValue(0)
            else:
                self.bar.setRange(0, 0)
            self.status.setText(f"{stage.value}…")
        self.status.setStyleSheet("")
        self.action.hide()

    def set_done(self, path: str, quality: str, skipped: bool = False) -> None:
        self.stage = Stage.SKIPPED if skipped else Stage.DONE
        self.path = path
        self.bar.setRange(0, 1000)
        self.bar.setValue(1000)
        self.bar.setProperty("state", "done")
        self._repolish(self.bar)
        self.bar.show()
        label = self.stage.value + (f" · {quality}" if quality else "")
        self.status.setText(label)
        self.status.setStyleSheet(f"color: {theme.SUCCESS};")
        self.action.setIcon(icons.icon("folder", 16, theme.TEXT))
        self.action.setToolTip("Mostrar en la carpeta")
        self.action.show()

    def set_failed(self, message: str) -> None:
        self.stage = Stage.FAILED
        self.bar.setRange(0, 1000)
        self.bar.setValue(1000)
        self.bar.setProperty("state", "failed")
        self._repolish(self.bar)
        self.status.setText(f"Error: {message}")
        self.status.setToolTip(message)
        self.status.setStyleSheet(f"color: {theme.ERROR};")
        self.action.setIcon(icons.icon("retry", 16, theme.TEXT))
        self.action.setToolTip("Reintentar")
        self.action.show()

    def set_cancelled(self) -> None:
        self.set_pending()

    @property
    def is_busy(self) -> bool:
        return self.stage in (Stage.QUEUED, Stage.FETCHING, Stage.DOWNLOADING,
                              Stage.CONVERTING, Stage.TAGGING)

    @property
    def is_finished(self) -> bool:
        return self.stage in (Stage.DONE, Stage.SKIPPED)

    def _on_action(self):
        if self.stage is Stage.FAILED:
            self.retry_requested.emit(self.key)
        elif self.path:
            self.open_requested.emit(self.path)

    @staticmethod
    def _repolish(w: QWidget):
        w.style().unpolish(w)
        w.style().polish(w)
