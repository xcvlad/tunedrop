"""Tarjetas de resultado y de la lista de descarga."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
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


class ResultCard(QWidget):
    """Una canción encontrada, con botón para añadirla o quitarla de la lista."""

    toggled = Signal(object)  # Track

    COVER = QSize(112, 63)

    def __init__(self, track: Track, parent=None):
        super().__init__(parent)
        self.track = track
        self.setObjectName("Card")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)

        self.cover = QLabel()
        self.cover.setFixedSize(self.COVER)
        self.cover.setPixmap(placeholder_cover(self.COVER.width(), self.COVER.height()))

        self.title = QLabel()
        self.title.setObjectName("CardTitle")
        _elide(self.title, track.title)
        meta = " · ".join(x for x in (track.channel, track.duration_text) if x)
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
