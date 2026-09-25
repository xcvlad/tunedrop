# ============================================================
#  Instalador de tunedrop para Windows en un solo comando.
#
#  Se usa así (copiar y pegar en PowerShell; no hace falta ser administrador):
#      irm https://raw.githubusercontent.com/xcvlad/tunedrop/main/instalar/windows.ps1 | iex
#
#  Qué hace:
#  1. Busca la última versión publicada en GitHub (Releases).
#  2. Descarga el instalador tunedrop-X.Y.Z-setup.exe (no necesitas Python).
#  3. Lo ejecuta sin preguntas: se instala solo para tu usuario, con acceso
#     en el menú Inicio y en el escritorio.
#
#  Volver a ejecutarlo actualiza a la última versión.
#  Para desinstalar: Configuración > Aplicaciones > tunedrop > Desinstalar.
#
#  Todo va dentro de una función y se usa «return» en vez de «exit»:
#  con «irm | iex», «exit» cerraría la ventana de PowerShell del usuario.
# ============================================================

function Install-Tunedrop {
    $ErrorActionPreference = "Stop"
    $ProgressPreference = "SilentlyContinue"   # la barra de progreso de PowerShell 5 hace la descarga muy lenta
    $repo = "xcvlad/tunedrop"

    # PowerShell 5.1 no activa TLS 1.2 por defecto, y GitHub lo exige.
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

    Write-Host ""
    Write-Host " === Instalando tunedrop ===" -ForegroundColor Cyan
    Write-Host ""

    # --- 1. Buscar la última versión --------------------------
    # La pagina .../releases/latest redirige a la ultima version, por ejemplo
    # .../releases/tag/v0.1.0. Nos quedamos con el final («v0.1.0»).
    # No usamos la API de GitHub porque solo permite 60 consultas por hora
    # desde la misma red (en un aula, varios alumnos se quedarian sin instalar).
    Write-Host " [1/3] Buscando la ultima version ..."
    try {
        $r = Invoke-WebRequest "https://github.com/$repo/releases/latest" -Method Head -UseBasicParsing
        if ($r.BaseResponse.ResponseUri) { $final = $r.BaseResponse.ResponseUri.AbsoluteUri }      # PowerShell 5
        else { $final = $r.BaseResponse.RequestMessage.RequestUri.AbsoluteUri }                     # PowerShell 7
    } catch {
        $final = ""
    }
    $etiqueta = $final.Split("/")[-1]
    if (-not $etiqueta.StartsWith("v")) {
        Write-Host " [X] No se encontro ninguna version publicada en https://github.com/$repo/releases" -ForegroundColor Red
        return
    }
    $archivo = "tunedrop-$($etiqueta.Substring(1))-setup.exe"      # «v0.1.0» -> «tunedrop-0.1.0-setup.exe»
    Write-Host "       $archivo"

    # --- 2. Descargar ------------------------------------------
    Write-Host " [2/3] Descargando (unos 115 MB) ..."
    $destino = Join-Path $env:TEMP $archivo
    try {
        Invoke-WebRequest "https://github.com/$repo/releases/download/$etiqueta/$archivo" -OutFile $destino -UseBasicParsing
    } catch {
        Write-Host " [X] No se pudo descargar $archivo. Comprueba tu conexion a internet." -ForegroundColor Red
        return
    }

    # --- 3. Instalar sin preguntas ------------------------------
    # Opciones de Inno Setup: /VERYSILENT sin ventanas, /TASKS crea el icono del escritorio.
    Write-Host " [3/3] Instalando ..."
    $p = Start-Process $destino -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/TASKS="desktopicon"' -Wait -PassThru
    Remove-Item $destino -ErrorAction SilentlyContinue
    if ($p.ExitCode -ne 0) {
        Write-Host " [X] El instalador termino con el codigo $($p.ExitCode)." -ForegroundColor Red
        return
    }

    Write-Host ""
    Write-Host " === Listo. Abre tunedrop desde el menu Inicio o el escritorio ===" -ForegroundColor Green
    Write-Host ""
    $exe = Join-Path $env:LOCALAPPDATA "Programs\tunedrop\tunedrop.exe"
    if (Test-Path $exe) { Start-Process $exe }
}

Install-Tunedrop
