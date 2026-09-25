@echo off
REM ============================================================
REM  PASO 1: prepara tunedrop en este ordenador (solo una vez).
REM  - Comprueba que Python esta instalado.
REM  - Crea un "entorno virtual" (.venv): una carpeta con las
REM    librerias del proyecto, sin tocar el resto del sistema.
REM  - Instala las librerias de requirements.txt.
REM  - Descarga ffmpeg en bin\ si no lo tienes.
REM ============================================================
chcp 65001 >nul
REM Este script vive en desde-el-codigo\, pero trabaja en la carpeta del proyecto (un nivel arriba).
cd /d "%~dp0.."

echo.
echo  === Instalando tunedrop ===
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo  [X] No se encuentra Python.
    echo      Instalalo desde https://www.python.org/downloads/
    echo      y marca la casilla "Add python.exe to PATH" al instalar.
    echo      Luego vuelve a ejecutar este archivo.
    pause
    exit /b 1
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo  [X] Tu Python es demasiado antiguo. Hace falta la version 3.10 o superior.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo  [1/3] Creando el entorno virtual .venv ...
    python -m venv .venv || goto :error
) else (
    echo  [1/3] El entorno virtual .venv ya existe.
)

echo  [2/3] Instalando librerias (puede tardar un par de minutos) ...
".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet || goto :error
".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet || goto :error

echo  [3/3] Comprobando ffmpeg ...
where ffmpeg >nul 2>nul
if errorlevel 1 (
    ".venv\Scripts\python.exe" packaging\descargar_ffmpeg.py || goto :error
) else (
    echo        ffmpeg ya esta instalado en el sistema.
)

echo.
echo  === Todo listo. Ahora abre la app con desde-el-codigo\2_abrir_tunedrop.bat ===
echo.
pause
exit /b 0

:error
echo.
echo  [X] Algo ha fallado. Lee el mensaje de arriba para ver el motivo.
pause
exit /b 1
