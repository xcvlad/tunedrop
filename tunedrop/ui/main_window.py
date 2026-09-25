from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QThreadPool, QTimer, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
    QMessageBox, QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from ..core import search as search_mod
from ..core.downloader import DownloadOptions, Stage
from ..core.history import History
from ..core.models import AudioFormat, Track
from ..core.runtime import MissingToolError, ffmpeg_path
from ..core.settings import Settings
from . import icons, theme
from .settings_dialog import SettingsDialog
from .widgets import QueueCard, ResultCard
from .workers import DownloadManager, ThumbnailLoader, start_search


def track_key(track: Track) -> str:
    return History.key(track.source, track.id)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("tunedrop")
        self.resize(1280, 800)
        self.setMinimumSize(960, 600)
        self.setAcceptDrops(True)

        self.settings = Settings.load()
        self.history = History()
        self.thumbs = ThumbnailLoader(self)
        self.search_pool = QThreadPool(self)
        self.search_pool.setMaxThreadCount(2)
        self.downloads = DownloadManager(self.settings.concurrent, self)
        self.downloads.progress.connect(self._on_progress)
        self.downloads.finished.connect(self._on_finished)
        self.downloads.failed.connect(self._on_failed)
        self.downloads.cancelled.connect(self._on_cancelled)

        self._search_token = 0
        self._last_clipboard = ""
        self._result_cards: dict[str, ResultCard] = {}
        self._queue_cards: dict[str, QueueCard] = {}
        self._queue_items: dict[str, QListWidgetItem] = {}

        self._build_ui()
        self._update_footer()
        QTimer.singleShot(300, self._check_tools)

    # ------------------------------------------------------------------ UI --

    def _build_ui(self):
        root = QWidget()
        outer = QVBoxLayout(root)
        outer.setContentsMargins(24, 18, 24, 20)
        outer.setSpacing(16)

        # Cabecera
        logo = QLabel(f'tune<span style="color:{theme.ACCENT_2}">drop</span>')
        logo.setObjectName("Logo")
        logo.setTextFormat(Qt.RichText)
        tagline = QLabel("Busca, elige y descarga tu música lista para cualquier reproductor")
        tagline.setObjectName("Tagline")
        settings_btn = QPushButton()
        settings_btn.setObjectName("Icon")
        settings_btn.setIcon(icons.icon("settings", 20, theme.MUTED))
        settings_btn.setIconSize(settings_btn.iconSize() * 1.1)
        settings_btn.setToolTip("Ajustes")
        settings_btn.setCursor(Qt.PointingHandCursor)
        settings_btn.clicked.connect(self._open_settings)
        header = QHBoxLayout()
        header.addWidget(logo)
        header.addSpacing(12)
        header.addWidget(tagline, 0, Qt.AlignBottom)
        header.addStretch()
        header.addWidget(settings_btn)
        outer.addLayout(header)

        # Buscador
        self.search = QLineEdit()
        self.search.setObjectName("Search")
        self.search.setPlaceholderText(
            "Busca una canción o artista… o pega un enlace de YouTube, playlist, SoundCloud, Bandcamp"
        )
        self.search.addAction(icons.icon("search", 18, theme.MUTED), QLineEdit.LeadingPosition)
        self.search.setClearButtonEnabled(True)
        self.search.returnPressed.connect(self._do_search)
        self.search_btn = QPushButton("Buscar")
        self.search_btn.setObjectName("Primary")
        self.search_btn.setMinimumHeight(48)
        self.search_btn.setMinimumWidth(120)
        self.search_btn.setCursor(Qt.PointingHandCursor)
        self.search_btn.clicked.connect(self._do_search)
        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        search_row.addWidget(self.search, 1)
        search_row.addWidget(self.search_btn)
        outer.addLayout(search_row)

        # Aviso de enlace copiado
        self.clip_banner = QPushButton()
        self.clip_banner.setObjectName("Link")
        self.clip_banner.setIcon(icons.icon("link", 15, theme.ACCENT_2))
        self.clip_banner.setCursor(Qt.PointingHandCursor)
        self.clip_banner.clicked.connect(self._use_clipboard)
        self.clip_banner.hide()
        outer.addWidget(self.clip_banner, 0, Qt.AlignLeft)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_results_panel())
        splitter.addWidget(self._build_queue_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([740, 480])
        outer.addWidget(splitter, 1)

        self.toast = QLabel(root)
        self.toast.setObjectName("Toast")
        self.toast.hide()
        self._toast_timer = QTimer(self, singleShot=True, timeout=self.toast.hide)

        self.setCentralWidget(root)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.search.setFocus)
        QShortcut(QKeySequence("Ctrl+L"), self, activated=self.search.setFocus)

    def _panel(self, title: str) -> tuple[QWidget, QVBoxLayout, QHBoxLayout]:
        panel = QWidget()
        panel.setObjectName("Panel")
        panel.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        head = QHBoxLayout()
        label = QLabel(title)
        label.setMinimumHeight(36)
        label.setObjectName("PanelTitle")
        head.addWidget(label)
        head.addStretch()
        layout.addLayout(head)
        return panel, layout, head

    def _build_list(self) -> QListWidget:
        lst = QListWidget()
        lst.setSpacing(4)
        lst.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        lst.verticalScrollBar().setSingleStep(18)
        lst.setSelectionMode(QListWidget.NoSelection)
        lst.setFocusPolicy(Qt.NoFocus)
        return lst

    def _build_results_panel(self) -> QWidget:
        panel, layout, head = self._panel("Resultados")
        self.results_count = QLabel()
        self.results_count.setObjectName("Muted")
        self.add_all_btn = QPushButton("  Añadir todas")
        self.add_all_btn.setIcon(icons.icon("list-plus", 16))
        self.add_all_btn.setCursor(Qt.PointingHandCursor)
        self.add_all_btn.clicked.connect(self._add_all)
        self.add_all_btn.hide()
        head.addWidget(self.results_count)
        head.addSpacing(8)
        head.addWidget(self.add_all_btn)

        self.results = self._build_list()
        self.results_empty = QLabel(
            "Escribe arriba lo que quieras escuchar y pulsa Intro.\n\n"
            "También puedes pegar o arrastrar aquí un enlace a un vídeo, una playlist o un álbum."
        )
        self.results_empty.setObjectName("Empty")
        self.results_empty.setAlignment(Qt.AlignCenter)
        self.results_empty.setWordWrap(True)
        layout.addWidget(self.results_empty, 1)
        layout.addWidget(self.results, 1)
        self.results.hide()
        return panel

    def _build_queue_panel(self) -> QWidget:
        panel, layout, head = self._panel("Tu lista")
        self.clear_done_btn = QPushButton("Limpiar completadas")
        self.clear_done_btn.setObjectName("Link")
        self.clear_done_btn.setCursor(Qt.PointingHandCursor)
        self.clear_done_btn.clicked.connect(self._clear_finished)
        open_btn = QPushButton()
        open_btn.setObjectName("Icon")
        open_btn.setIcon(icons.icon("folder", 18, theme.MUTED))
        open_btn.setToolTip("Abrir la carpeta de música")
        open_btn.setCursor(Qt.PointingHandCursor)
        open_btn.clicked.connect(self._open_music_folder)
        head.addWidget(self.clear_done_btn)
        head.addWidget(open_btn)

        self.queue = self._build_list()
        self.queue_empty = QLabel("Pulsa + en las canciones que quieras\ny aparecerán aquí.")
        self.queue_empty.setObjectName("Empty")
        self.queue_empty.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.queue_empty, 1)
        layout.addWidget(self.queue, 1)
        self.queue.hide()

        self.summary = QLabel()
        self.summary.setObjectName("Muted")
        self.format_combo = QComboBox()
        for fmt in AudioFormat:
            self.format_combo.addItem(fmt.label.split(" · ")[0], fmt.value)
        self.format_combo.setCurrentIndex(self.format_combo.findData(self.settings.audio_format))
        self.format_combo.setToolTip("Formato de salida")
        self.format_combo.currentIndexChanged.connect(self._on_format_changed)
        footer = QHBoxLayout()
        footer.addWidget(self.summary, 1)
        footer.addWidget(self.format_combo)
        layout.addLayout(footer)

        self.download_btn = QPushButton()
        self.download_btn.setObjectName("Primary")
        self.download_btn.setMinimumHeight(50)
        self.download_btn.setStyleSheet("font-size: 12pt; border-radius: 14px;")
        self.download_btn.setIcon(icons.icon("download", 18, "#ffffff", 2.4))
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.clicked.connect(self._download_all)
        layout.addWidget(self.download_btn)
        return panel

    # ------------------------------------------------------------ búsqueda --

    def _do_search(self):
        text = self.search.text().strip()
        if not text:
            return
        self._search_token += 1
        self.search_btn.setEnabled(False)
        self.search_btn.setText("Buscando…")
        self.results_count.setText("")
        self.add_all_btn.hide()
        self._show_results_message("Buscando…" if not search_mod.is_url(text) else "Leyendo el enlace…")
        start_search(self.search_pool, self._search_token, text,
                     self._on_search_done, self._on_search_failed)

    def _on_search_done(self, token: int, tracks: list):
        if token != self._search_token:
            return
        self._reset_search_button()
        self.results.clear()
        self._result_cards.clear()
        if not tracks:
            self._show_results_message("No se encontró nada. Prueba con otras palabras.")
            return
        for track in tracks:
            card = ResultCard(track)
            card.toggled.connect(self._toggle_track)
            key = track_key(track)
            card.set_added(key in self._queue_cards)
            card.set_downloaded(self.history.contains(track.source, track.id))
            item = QListWidgetItem(self.results)
            item.setSizeHint(card.sizeHint())
            self.results.setItemWidget(item, card)
            self._result_cards[key] = card
            self.thumbs.load(track.thumbnail, card.set_cover)
        self.results_empty.hide()
        self.results.show()
        self.results.scrollToTop()
        n = len(tracks)
        self.results_count.setText(f"{n} {'canción' if n == 1 else 'canciones'}")
        self.add_all_btn.setVisible(n > 1)
        # Un enlace a una sola canción se añade directamente: pegar y listo.
        if n == 1 and search_mod.is_url(self.search.text()):
            self._add_tracks(tracks)

    def _on_search_failed(self, token: int, message: str):
        if token != self._search_token:
            return
        self._reset_search_button()
        self._show_results_message(f"No se pudo buscar: {message}")

    def _reset_search_button(self):
        self.search_btn.setEnabled(True)
        self.search_btn.setText("Buscar")

    def _show_results_message(self, text: str):
        self.results.hide()
        self.results_empty.setText(text)
        self.results_empty.show()

    # --------------------------------------------------------------- lista --

    def _toggle_track(self, track: Track):
        key = track_key(track)
        if key in self._queue_cards:
            self._remove_from_queue(key)
        else:
            self._add_tracks([track])

    def _add_all(self):
        tracks = [c.track for c in self._result_cards.values()]
        added = self._add_tracks(tracks)
        self._show_toast(f"{added} canciones añadidas a tu lista" if added else "Ya estaban todas en tu lista")

    def _add_tracks(self, tracks: list[Track]) -> int:
        added = 0
        for track in tracks:
            key = track_key(track)
            if key in self._queue_cards:
                continue
            card = QueueCard(key, track)
            card.remove_requested.connect(self._remove_from_queue)
            card.retry_requested.connect(lambda k: self._start_download([k]))
            card.open_requested.connect(self._reveal_file)
            item = QListWidgetItem(self.queue)
            item.setSizeHint(card.sizeHint())
            self.queue.setItemWidget(item, card)
            self._queue_cards[key] = card
            self._queue_items[key] = item
            self.thumbs.load(track.thumbnail, card.set_cover)
            if key in self._result_cards:
                self._result_cards[key].set_added(True)
            added += 1
        if added:
            self.queue.scrollToBottom()
        self._update_footer()
        return added

    def _remove_from_queue(self, key: str):
        self.downloads.cancel(key)
        item = self._queue_items.pop(key, None)
        self._queue_cards.pop(key, None)
        if item is not None:
            self.queue.takeItem(self.queue.row(item))
        if key in self._result_cards:
            self._result_cards[key].set_added(False)
        self._update_footer()

    def _clear_finished(self):
        for key, card in list(self._queue_cards.items()):
            if card.is_finished:
                self._remove_from_queue(key)

    def _update_footer(self):
        cards = list(self._queue_cards.values())
        has = bool(cards)
        self.queue.setVisible(has)
        self.queue_empty.setVisible(not has)
        pending = [c for c in cards if not c.is_busy and not c.is_finished]
        busy = [c for c in cards if c.is_busy]
        done = [c for c in cards if c.is_finished]
        total = sum(c.track.duration or 0 for c in cards)
        parts = [f"{len(cards)} {'canción' if len(cards) == 1 else 'canciones'}"]
        if total:
            h, m = divmod(total // 60, 60)
            parts.append(f"{h} h {m} min" if h else f"{m} min")
        if done:
            parts.append(f"{len(done)} listas")
        self.summary.setText(" · ".join(parts) if has else "")
        self.clear_done_btn.setVisible(bool(done))
        if busy and not pending:
            self.download_btn.setText(f"  Descargando {len(busy)}…")
            self.download_btn.setEnabled(False)
        elif pending:
            self.download_btn.setText(f"  Descargar ({len(pending)})")
            self.download_btn.setEnabled(True)
        else:
            self.download_btn.setText("  Descargar")
            self.download_btn.setEnabled(False)

    # ------------------------------------------------------------ descarga --

    def _download_all(self):
        keys = [k for k, c in self._queue_cards.items() if not c.is_busy and not c.is_finished]
        self._start_download(keys)

    def _start_download(self, keys: list[str]):
        if not self._check_tools():
            return
        options = DownloadOptions(
            output_dir=Path(self.settings.output_dir),
            audio_format=self.settings.format,
            normalize=self.settings.normalize,
        )
        for key in keys:
            card = self._queue_cards.get(key)
            if not card:
                continue
            t = card.track
            existing = self.history.file_for(t.source, t.id)
            if self.settings.skip_downloaded and existing:
                card.set_done(str(existing), "", skipped=True)
                continue
            self.downloads.enqueue(key, t, options)
        self._update_footer()

    def _on_progress(self, key: str, stage: str, fraction: float, extra: str):
        card = self._queue_cards.get(key)
        if card:
            card.set_progress(Stage(stage), fraction, extra)
            self._update_footer()

    def _on_finished(self, key: str, path: str, quality: str):
        card = self._queue_cards.get(key)
        track = card.track if card else None
        if track:
            self.history.add(track.source, track.id, Path(path), track.title)
            card.set_done(path, quality)
            if key in self._result_cards:
                self._result_cards[key].set_downloaded(True)
        self._update_footer()
        if self.downloads.active_count == 0:
            done = sum(1 for c in self._queue_cards.values() if c.stage is Stage.DONE)
            if done:
                self._show_toast("Descargas terminadas")

    def _on_failed(self, key: str, message: str):
        card = self._queue_cards.get(key)
        if card:
            card.set_failed(message)
        self._update_footer()

    def _on_cancelled(self, key: str):
        card = self._queue_cards.get(key)
        if card:
            card.set_cancelled()
        self._update_footer()

    # ----------------------------------------------------------- utilidades --

    def _check_tools(self) -> bool:
        try:
            ffmpeg_path()
            return True
        except MissingToolError as exc:
            QMessageBox.warning(self, "Falta ffmpeg", str(exc))
            return False

    def _on_format_changed(self):
        self.settings.audio_format = self.format_combo.currentData()
        self.settings.save()

    def _open_settings(self):
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self.settings = dialog.result_settings()
            self.settings.save()
            self.downloads.set_concurrency(self.settings.concurrent)
            self.format_combo.blockSignals(True)
            self.format_combo.setCurrentIndex(self.format_combo.findData(self.settings.audio_format))
            self.format_combo.blockSignals(False)

    def _open_music_folder(self):
        folder = Path(self.settings.output_dir)
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def _reveal_file(self, path: str):
        if not Path(path).exists():
            self._show_toast("Ese archivo ya no existe")
            return
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(path).parent)))

    def _show_toast(self, text: str, msecs: int = 2800):
        self.toast.setText(text)
        self.toast.adjustSize()
        root = self.centralWidget()
        self.toast.move((root.width() - self.toast.width()) // 2, root.height() - self.toast.height() - 28)
        self.toast.raise_()
        self.toast.show()
        self._toast_timer.start(msecs)

    # Enlaces del portapapeles: al volver a la ventana, ofrece usar el enlace copiado.
    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == event.Type.ActivationChange and self.isActiveWindow():
            text = (QGuiApplication.clipboard().text() or "").strip()
            if text and text != self._last_clipboard and search_mod.is_url(text) and len(text) < 500:
                self._last_clipboard = text
                self.clip_banner.setText(f"  Enlace copiado: {text[:70]}{'…' if len(text) > 70 else ''}  ·  Pulsa para abrirlo")
                self.clip_banner.setProperty("url", text)
                self.clip_banner.show()

    def _use_clipboard(self):
        self.search.setText(self.clip_banner.property("url"))
        self.clip_banner.hide()
        self._do_search()

    # Arrastrar y soltar enlaces
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        mime = event.mimeData()
        text = mime.urls()[0].toString() if mime.hasUrls() else mime.text()
        if text and search_mod.is_url(text.strip()):
            self.search.setText(text.strip())
            self._do_search()

    def closeEvent(self, event):
        busy = sum(1 for c in self._queue_cards.values() if c.is_busy)
        if busy:
            answer = QMessageBox.question(
                self, "Descargas en curso",
                f"Hay {busy} descargas en curso. ¿Salir y cancelarlas?",
            )
            if answer != QMessageBox.Yes:
                event.ignore()
                return
        self.downloads.cancel_all()
        self.downloads.wait(3000)
        event.accept()
