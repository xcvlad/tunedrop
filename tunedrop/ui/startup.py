"""Lo que pasa al abrir la app, antes de que aparezca la ventana principal.

- Una sola tunedrop: si ya está abierta (o abriéndose) y la vuelves a abrir, no
  sale otra; se le pide a la que ya existe que se ponga delante.
- Pantalla de carga: un recuadro «Abriendo tunedrop…» que aparece enseguida,
  mientras se prepara la ventana principal, para que se vea que está en marcha.

Por qué tarda en abrirse: el programa ocupa cientos de MB (Python, Qt, ffmpeg,
Deno) y, al abrirlo, Windows y el antivirus revisan sus archivos. Por eso
yt-dlp, que también tarda en cargarse, no se carga hasta que la ventana ya se ve.
"""

from __future__ import annotations

import getpass
import threading

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QGuiApplication, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QSplashScreen, QWidget

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
    p.drawText(QRectF(108, 62, ancho - 120, 24), Qt.AlignmentFlag.AlignVCenter, "Abriendo tunedrop…")
    p.end()

    splash = QSplashScreen(imagen)
    splash.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)   # esquinas redondeadas
    return splash


def preload_in_background() -> None:
    """Carga yt-dlp en segundo plano cuando la ventana ya se ve, para que la
    primera búsqueda no tenga que esperarlo."""
    threading.Thread(target=lambda: __import__("yt_dlp"), daemon=True).start()
