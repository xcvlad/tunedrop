from __future__ import annotations

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
        self.lyrics = QCheckBox("Añadir la letra de cada canción")
        self.lyrics.setToolTip("Va dentro del MP3 o M4A. El iPod la muestra al pulsar el botón central.")
        self.lyrics.setChecked(settings.lyrics)
        self.lrc = QCheckBox("Guardar también un archivo .lrc con la letra sincronizada")
        self.lrc.setToolTip(
            "Un archivo con la letra y el momento en que se canta cada línea, junto a la canción.\n"
            "Algunos reproductores (Rockbox y muchos MP3) la muestran a la vez que suena.")
        self.lrc.setChecked(settings.lrc_file)
        # El .lrc solo tiene sentido si se buscan las letras.
        self.lrc.setEnabled(settings.lyrics)
        self.lyrics.toggled.connect(self.lrc.setEnabled)
        self.updates = QCheckBox("Avisar si hay una versión nueva de tunedrop")
        self.updates.setToolTip("Al abrir la app, pregunta a GitHub cuál es la última versión.")
        self.updates.setChecked(settings.check_updates)
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
        form.addRow("Letras", self.lyrics)
        form.addRow("", self.lrc)
        form.addRow("Actualizaciones", self.updates)

        note = QLabel(
            "Sobre la calidad: YouTube entrega el audio a ~128-160 kbps (Opus o AAC). "
            "MP3 V0 conserva todo lo que hay con un buen tamaño; 320 kbps no añade calidad real. "
            "M4A copia el audio AAC original sin recodificar y el iPod lo lee de forma nativa.\n\n"
            "Las letras salen de LRCLIB (lrclib.net), una base de datos de letras gratuita y abierta. "
            "Si una canción no está, se descarga igual, sin letra."
        )
        note.setObjectName("Muted")
        note.setWordWrap(True)

        from yt_dlp.version import __version__ as ytdlp_version  # ver ui/startup.py

        versions = QLabel(f"tunedrop {__version__} · yt-dlp {ytdlp_version}")
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
        s.lyrics = self.lyrics.isChecked()
        s.lrc_file = self.lrc.isChecked()
        s.check_updates = self.updates.isChecked()
        s.concurrent = self.concurrent.value()
        return s
