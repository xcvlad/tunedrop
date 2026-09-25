"""Punto de entrada: es lo que se ejecuta con `python -m tunedrop` (y dentro del .exe)."""

from __future__ import annotations

import sys
from pathlib import Path

ICONO = Path(__file__).resolve().parent / "assets" / "icono.png"


def main() -> int:
    if "--comprobar" in sys.argv:
        from .comprobar import ejecutar

        i = sys.argv.index("--comprobar")
        return ejecutar(sys.argv[i + 1:])

    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from . import APP_NAME
    from .ui import theme
    from .ui.main_window import MainWindow

    if sys.platform == "win32":
        # Hace que Windows muestre nuestro icono en la barra de tareas y no el de Python.
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_NAME)

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    # En Linux (sobre todo con Wayland) enlaza la ventana con su tunedrop.desktop,
    # para que el escritorio muestre el nombre y el icono correctos.
    app.setDesktopFileName(APP_NAME)
    app.setStyle("Fusion")
    app.setStyleSheet(theme.STYLESHEET)
    app.setWindowIcon(QIcon(str(ICONO)))
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
