@echo off
REM ============================================================
REM  PASO 3 (opcional): crea el programa para distribuir.
REM  Resultado en la carpeta dist\ :
REM   - tunedrop-X.Y.Z-portable.zip  (descomprimir y usar)
REM   - tunedrop-X.Y.Z-setup.exe     (instalador, si tienes Inno Setup)
REM  Todo el proceso esta en packaging\build.py
REM ============================================================
chcp 65001 >nul
REM Este script vive en desde-el-codigo\, pero trabaja en la carpeta del proyecto (un nivel arriba).
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo  Primero tienes que ejecutar desde-el-codigo\1_instalar.bat
    pause
    exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt --quiet || goto :error
".venv\Scripts\python.exe" packaging\build.py || goto :error

echo.
echo  === Hecho. Mira la carpeta dist\ ===
explorer dist
pause
exit /b 0

:error
echo.
echo  [X] Algo ha fallado. Lee el mensaje de arriba para ver el motivo.
pause
exit /b 1
