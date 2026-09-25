from __future__ import annotations

import yt_dlp
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QSpinBox, QVBoxLayout,
)

from .. import __version__
from ..core.models import AudioFormat
from ..core.settings import Settings


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajustes")
        self.setMinimumWidth(560)
        self._settings = settings

        self.folder = QLineEdit(settings.output_dir)
        browse = QPushButton("Examinar…")
        browse.clicked.connect(self._browse)
        folder_row = QHBoxLayout()
        folder_row.addWidget(self.folder, 1)
        folder_row.addWidget(browse)

        self.format = QComboBox()
        for fmt in AudioFormat:
            self.format.addItem(fmt.label, fmt.value)
        self.format.setCurrentIndex(self.format.findData(settings.audio_format))

        self.normalize = QCheckBox("Igualar el volumen de todas las canciones (-14 LUFS)")
        self.normalize.setChecked(settings.normalize)
        self.skip = QCheckBox("No volver a descargar canciones que ya tengo")
        self.skip.setChecked(settings.skip_downloaded)
        self.concurrent = QSpinBox()
        self.concurrent.setRange(1, 6)
        self.concurrent.setValue(settings.concurrent)

        form = QFormLayout()
        form.setSpacing(14)
        form.addRow("Carpeta de música", folder_row)
        form.addRow("Formato", self.format)
        form.addRow("Descargas a la vez", self.concurrent)
        form.addRow("", self.normalize)
        form.addRow("", self.skip)

        note = QLabel(
            "Sobre la calidad: YouTube entrega el audio a ~128-160 kbps (Opus o AAC). "
            "MP3 V0 conserva todo lo que hay con un buen tamaño; 320 kbps no añade calidad real. "
            "M4A copia el audio AAC original sin recodificar y el iPod lo lee de forma nativa."
        )
        note.setObjectName("Muted")
        note.setWordWrap(True)

        versions = QLabel(f"tunedrop {__version__} · yt-dlp {yt_dlp.version.__version__}")
        versions.setObjectName("Muted")

        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Guardar")
        save.setObjectName("Primary")
        save.setDefault(True)
        save.clicked.connect(self.accept)
        buttons = QHBoxLayout()
        buttons.addWidget(versions)
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(save)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(18)
        title = QLabel("Ajustes")
        title.setObjectName("PanelTitle")
        layout.addWidget(title)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addStretch()
        layout.addLayout(buttons)

    def _browse(self):
        path = QFileDialog.getExistingDirectory(self, "Carpeta de música", self.folder.text())
        if path:
            self.folder.setText(path)

    def result_settings(self) -> Settings:
        s = self._settings
        s.output_dir = self.folder.text().strip() or s.output_dir
        s.audio_format = self.format.currentData()
        s.normalize = self.normalize.isChecked()
        s.skip_downloaded = self.skip.isChecked()
        s.concurrent = self.concurrent.value()
        return s
