"""Lo que pasa al abrir la app, antes de que aparezca la ventana principal.

- Una sola tunedrop: si ya está abierta (o abriéndose) y la vuelves a abrir, no
  sale otra; se le pide a la que ya existe que se ponga delante.
- Pantalla de carga: un recuadro «Abriendo tunedrop…» que aparece enseguida,
  mientras se prepara la ventana principal, para que se vea que está en marcha.
- Idioma: los textos que pone Qt (botones Sí/No, el selector de carpetas…) en
  el idioma de la app (ver tunedrop/idioma.py).
- Reiniciar: al cambiar de idioma o al actualizar en Linux, la app se cierra y
  se vuelve a abrir sola.

Por qué tarda en abrirse: el programa ocupa cientos de MB (Python, Qt, ffmpeg,
Deno) y, al abrirlo, Windows y el antivirus revisan sus archivos. Por eso
yt-dlp, que también tarda en cargarse, no se carga hasta que la ventana ya se ve.
"""

from __future__ import annotations

import getpass
import os
import subprocess
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QSplashScreen, QWidget

from .. import idioma
from ..core import updates
from ..idioma import tr
from . import theme

# La misma lista de letras que theme.py: Segoe en Windows; Inter, Cantarell,
# Ubuntu o Noto en Linux (se usa la primera que exista).
LETRAS = ["Segoe UI", "Inter", "Cantarell", "Ubuntu", "Noto Sans", "DejaVu Sans"]


class SingleInstance:
    """Se asegura de que solo haya una tunedrop abierta por usuario.

    La primera tunedrop abre un «buzón» (QLocalServer: una tubería con nombre en
    Windows y un archivo especial en Linux). Las siguientes miran si ese buzón
    existe: si existe, dejan un aviso y se cierran; la primera, al recibirlo,
    se pone delante.
    """

    def __init__(self) -> None:
        try:
            usuario = getpass.getuser()
        except Exception:
            usuario = "usuario"
        # Un nombre por usuario: en un PC compartido, cada persona tiene su tunedrop.
        self.name = f"tunedrop-{usuario}"
        self.server: QLocalServer | None = None
        self.window: QWidget | None = None

    def notify_running(self) -> bool:
        """True si ya había una tunedrop abierta (y se le ha pedido que se muestre)."""
        socket = QLocalSocket()
        socket.connectToServer(self.name)
        if not socket.waitForConnected(500):
            return False
        socket.write(b"mostrar")
        socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        return True

    def listen(self) -> None:
        """Abre el buzón. Se hace nada más arrancar, antes de preparar la ventana,
        para que un segundo clic durante la carga tampoco abra otra tunedrop."""
        # En Linux, si la app se cerró de golpe, puede quedar el archivo del buzón
        # anterior y no dejaría abrir uno nuevo. Aquí ya sabemos que nadie lo usa.
        QLocalServer.removeServer(self.name)
        self.server = QLocalServer()
        self.server.newConnection.connect(self._on_new_connection)
        self.server.listen(self.name)

    def close(self) -> None:
        """Cierra el buzón (al salir de la app)."""
        if self.server is not None:
            self.server.close()

    def _on_new_connection(self) -> None:
        while self.server.hasPendingConnections():
            self.server.nextPendingConnection().deleteLater()
        # Si la ventana aún no existe, no hace falta nada: está a punto de salir.
        if self.window is not None:
            bring_to_front(self.window)


def bring_to_front(window: QWidget) -> None:
    """Muestra la ventana (aunque esté minimizada) y la pone delante de las demás."""
    window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized)
    window.show()
    window.raise_()
    window.activateWindow()


def splash_screen(icon_path: str) -> QSplashScreen:
    """Recuadro «Abriendo tunedrop…» con el icono y los colores de la app."""
    ancho, alto = 340, 120
    escala = QGuiApplication.primaryScreen().devicePixelRatio()   # pantallas con zoom
    imagen = QPixmap(int(ancho * escala), int(alto * escala))
    imagen.setDevicePixelRatio(escala)
    imagen.fill(Qt.GlobalColor.transparent)

    p = QPainter(imagen)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    fondo = QPainterPath()
    fondo.addRoundedRect(QRectF(0.5, 0.5, ancho - 1, alto - 1), 18, 18)
    p.fillPath(fondo, QColor(theme.SURFACE))
    p.setPen(QPen(QColor(theme.BORDER), 1))
    p.drawPath(fondo)

    p.drawPixmap(26, 28, QIcon(icon_path).pixmap(64, 64))
    p.setPen(QColor(theme.TEXT))
    titulo = QFont()
    titulo.setFamilies(LETRAS)
    titulo.setPixelSize(24)
    titulo.setBold(True)
    p.setFont(titulo)
    p.drawText(QRectF(108, 30, ancho - 120, 32), Qt.AlignmentFlag.AlignVCenter, "tunedrop")
    p.setPen(QColor(theme.MUTED))
    texto = QFont()
    texto.setFamilies(LETRAS)
    texto.setPixelSize(14)
    p.setFont(texto)
    p.drawText(QRectF(108, 62, ancho - 120, 24), Qt.AlignmentFlag.AlignVCenter, tr("Abriendo tunedrop…"))
    p.end()

    splash = QSplashScreen(imagen)
    splash.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)   # esquinas redondeadas
    return splash


def preload_in_background() -> None:
    """Carga yt-dlp en segundo plano cuando la ventana ya se ve, para que la
    primera búsqueda no tenga que esperarlo."""
    threading.Thread(target=lambda: __import__("yt_dlp"), daemon=True).start()


def load_qt_translations(app: QApplication) -> None:
    """Los textos que pone el propio Qt (los botones Sí y No de las preguntas,
    el selector de carpetas…) en el idioma de la app. Qt trae sus traducciones
    en archivos .qm; en inglés no hace falta ninguna. Si no las encuentra, esos
    botones salen en inglés, sin más."""
    if idioma.actual() != "es":
        return
    from PySide6.QtCore import QLibraryInfo, QTranslator

    traductor = QTranslator(app)   # con la app de «padre», vive lo mismo que ella
    carpeta = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if traductor.load("qtbase_es", carpeta):
        app.installTranslator(traductor)


def request_restart(window: QWidget) -> None:
    """Cierra la app y la vuelve a abrir. Si hay descargas, la ventana pregunta
    antes de cerrarse; si se decide no cerrar, no se reinicia."""
    app = QApplication.instance()
    app.setProperty("reiniciar", True)
    if not window.close():
        app.setProperty("reiniciar", False)


def restart_if_requested() -> None:
    """Abre otra vez tunedrop si se pidió reiniciar. La llama __main__.py al
    cerrarse la app (después de cerrar el buzón de SingleInstance: si no, la
    nueva creería que ya hay una tunedrop abierta y se cerraría)."""
    app = QApplication.instance()
    if app is None or not app.property("reiniciar"):
        return
    env = updates.clean_environment()
    if getattr(sys, "frozen", False):
        orden = [sys.executable]          # el programa compilado (tunedrop.exe)
    else:
        # Desde el código o con Nix: «python -m tunedrop», con las mismas carpetas
        # de librerías que esta (Nix las añade al arrancar, no en el entorno).
        orden = [sys.executable, "-m", "tunedrop"]
        carpetas = [str(Path(__file__).resolve().parents[2]), *(p for p in sys.path if p)]
        env["PYTHONPATH"] = os.pathsep.join(carpetas)
    try:
        subprocess.Popen(orden, env=env, start_new_session=True)
    except OSError:
        pass   # no se pudo: se abre a mano, como siempre
