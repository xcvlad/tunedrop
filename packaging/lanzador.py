"""Archivo de arranque que PyInstaller convierte en tunedrop.exe.

PyInstaller necesita un archivo .py como punto de entrada; este solo llama a la app.
"""

import sys

from tunedrop.__main__ import main

sys.exit(main())
