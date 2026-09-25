@echo off
REM ============================================================
REM  PASO 2: abre tunedrop.
REM  Usa pythonw.exe (Python sin ventana negra de consola).
REM ============================================================
chcp 65001 >nul
REM Este script vive en desde-el-codigo\, pero trabaja en la carpeta del proyecto (un nivel arriba).
cd /d "%~dp0.."

if not exist ".venv\Scripts\pythonw.exe" (
    echo  Primero tienes que ejecutar desde-el-codigo\1_instalar.bat
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" -m tunedrop
