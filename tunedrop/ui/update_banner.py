"""La franja «Hay una versión nueva de tunedrop» de arriba de la ventana.

Al abrir la app se comprueba en segundo plano (core/updates.py). Si hay versión
nueva, aparece esta franja con tres botones:
- Actualizar: vuelve a ejecutar el comando de instalar, que instala la nueva.
    * Windows: abre PowerShell con el comando y cierra tunedrop, para que el
      instalador pueda reemplazar sus archivos. Al terminar, la vuelve a abrir.
    * Linux: ejecuta el comando en segundo plano y después ofrece «Reiniciar».
    * NixOS, .zip portable o desde el código: la app no puede actualizarse sola;
      el botón no aparece y se explica qué hacer.
- Novedades: abre la página de la versión en GitHub.
- ✕: oculta el aviso hasta la próxima vez que se abra la app.
"""

from __future__ import annotations

import subprocess

from PySide6.QtCore import QObject, QRunnable, QThreadPool, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton

from .. import __version__, idioma
from ..core import updates
from ..idioma import tr
from . import icons, startup, theme


class _Signals(QObject):
    done = Signal(object)


class _Task(QRunnable):
    """Ejecuta una función en otro hilo, para que la ventana no se congele."""

    def __init__(self, fn, on_done):
        super().__init__()
        self.fn = fn
        self.signals = _Signals()
        self.signals.done.connect(on_done)

    def run(self):
        try:
            result = self.fn()
        except Exception:  # noqa: BLE001 - el aviso es un extra: nunca debe romper nada
            result = None
        self.signals.done.emit(result)


def _update_linux() -> bool:
    """Vuelve a ejecutar el comando de instalar de Linux. True si ha ido bien."""
    # TUNEDROP_IDIOMA: el instalador usa el idioma de la app y no pregunta.
    env = {**updates.clean_environment(), "TUNEDROP_IDIOMA": idioma.actual()}
    resultado = subprocess.run(
        ["bash", "-c", f"curl -fsSL {updates.INSTALAR_LINUX} | bash"],
        capture_output=True, text=True, timeout=900, env=env,
    )
    return resultado.returncode == 0


class UpdateBanner(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("UpdateBanner")
        self.version: str | None = None
        self.kind = updates.install_kind()
        self._tasks: list[_Task] = []   # para que Python no las borre mientras trabajan

        icono = QLabel()
        icono.setPixmap(icons.pixmap("download", 18, theme.ACCENT_2))
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.update_btn = QPushButton(tr("Actualizar"))
        self.update_btn.setObjectName("Primary")
        self.update_btn.clicked.connect(self._update)
        notes = QPushButton(tr("Novedades"))
        notes.setObjectName("Link")
        notes.clicked.connect(self._open_notes)
        close = QPushButton()
        close.setObjectName("Icon")
        close.setIcon(icons.icon("x", 16, theme.MUTED))
        close.setToolTip(tr("Ocultar hasta la próxima vez"))
        close.clicked.connect(self.hide)

        fila = QHBoxLayout(self)
        fila.setContentsMargins(14, 8, 8, 8)
        fila.setSpacing(10)
        fila.addWidget(icono)
        fila.addWidget(self.text, 1)
        fila.addWidget(self.update_btn)
        fila.addWidget(notes)
        fila.addWidget(close)
        self.hide()

    # --- 1. Comprobar -------------------------------------------------------------

    def start_check(self) -> None:
        self._run(updates.check, self._on_checked)

    def _on_checked(self, version: str | None) -> None:
        if not version:
            return
        self.version = version
        texto = tr("<b>Hay una versión nueva de tunedrop: {nueva}</b> (tienes la {tuya}).",
                   nueva=version, tuya=__version__)
        if self.kind in ("windows", "linux"):
            self.update_btn.show()
        else:
            self.update_btn.hide()
            texto += " " + updates.update_hint(self.kind)
        self.text.setText(texto)
        self.show()

    # --- 2. Actualizar -------------------------------------------------------------

    def _update(self) -> None:
        if self.kind == "windows":
            self._update_windows()
        elif self.kind == "linux":
            self.update_btn.setEnabled(False)
            self.update_btn.setText(tr("Actualizando…"))
            self.text.setText(tr("<b>Instalando tunedrop {version}…</b> Puedes seguir usando la app.",
                                 version=self.version))
            self._run(_update_linux, self._on_linux_updated)

    def _update_windows(self) -> None:
        # Primero se cierra la ventana (si hay descargas, pregunta). Si la persona
        # decide no cerrar, no se actualiza.
        if not self.window().close():
            return
        # PowerShell en una ventana propia con el comando de instalar de siempre.
        # Al final espera a que pulses Intro, para que se pueda leer si algo falla.
        # TUNEDROP_IDIOMA: el instalador usa el idioma de la app y no pregunta.
        cerrar = tr("Pulsa Intro para cerrar esta ventana")
        comando = (f"$env:TUNEDROP_IDIOMA = '{idioma.actual()}'; "
                   f"irm {updates.INSTALAR_WINDOWS} | iex; Write-Host ''; "
                   f"Read-Host '  {cerrar}'")
        subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", comando],
            creationflags=subprocess.CREATE_NEW_CONSOLE, env=updates.clean_environment(),
        )
        QApplication.quit()

    def _on_linux_updated(self, ok: bool | None) -> None:
        self.update_btn.setEnabled(True)
        if ok:
            self.text.setText(tr("<b>tunedrop {version} está instalada.</b> Reinicia la app para usarla.",
                                 version=self.version))
            self.update_btn.setText(tr("Reiniciar"))
            self.update_btn.clicked.disconnect()
            self.update_btn.clicked.connect(self._restart)
        else:
            self.update_btn.setText(tr("Reintentar"))
            self.text.setText(tr("<b>No se pudo actualizar.</b> Comprueba tu conexión, o descarga la versión "
                                 "nueva desde la página de novedades."))

    def _restart(self) -> None:
        startup.request_restart(self.window())

    # --- Otros ---------------------------------------------------------------------

    def _open_notes(self) -> None:
        etiqueta = f"tag/v{self.version}" if self.version else "latest"
        QDesktopServices.openUrl(QUrl(f"{updates.RELEASES}/{etiqueta}"))

    def _run(self, fn, on_done) -> None:
        task = _Task(fn, lambda result: self._finish(task, on_done, result))
        self._tasks.append(task)
        QThreadPool.globalInstance().start(task)

    def _finish(self, task: _Task, on_done, result) -> None:
        if task in self._tasks:
            self._tasks.remove(task)
        on_done(result)
