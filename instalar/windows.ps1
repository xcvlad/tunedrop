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

function Show-AvisoBloqueo {
    # Smart App Control (Windows 11) solo deja ejecutar programas firmados con un
    # certificado o muy conocidos. tunedrop todavia no esta firmado, asi que lo bloquea
    # sin opcion de "ejecutar de todas formas". No hay nada que el script pueda hacer.
    Write-Host ""
    Write-Host " [X] Windows no deja instalar tunedrop en este ordenador." -ForegroundColor Red
    Write-Host ""
    Write-Host "     Lo mas probable es que tengas activado 'Control inteligente de aplicaciones'"
    Write-Host "     (Smart App Control)."
    Write-Host "     Es una proteccion de Windows 11 que solo permite programas con firma digital,"
    Write-Host "     y tunedrop aun no la tiene. No es un virus ni un fallo de tu ordenador."
    Write-Host ""
    Write-Host "     Mas informacion: https://github.com/xcvlad/tunedrop#smart-app-control"
    Write-Host ""
}

function Install-Tunedrop {
    $ErrorActionPreference = "Stop"
    $ProgressPreference = "SilentlyContinue"   # la barra de progreso de PowerShell 5 hace la descarga muy lenta
    $repo = "xcvlad/tunedrop"

    # PowerShell 5.1 no activa TLS 1.2 por defecto, y GitHub lo exige.
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

    Write-Host ""
    Write-Host " === Instalando tunedrop ===" -ForegroundColor Cyan
    Write-Host ""

    # Antes de descargar 115 MB, comprobamos si Smart App Control lo va a bloquear.
    # Su estado se guarda en el registro: 0 = apagado, 1 = activado, 2 = en evaluacion.
    # (Cuando tunedrop este firmado, esta comprobacion se podra quitar.)
    $sac = (Get-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy" -ErrorAction SilentlyContinue).VerifiedAndReputablePolicyState
    if ($sac -eq 1) {
        Show-AvisoBloqueo
        return
    }

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
        Remove-Item $destino -ErrorAction SilentlyContinue       # por si quedo a medias
        Write-Host " [X] No se pudo descargar $archivo. Comprueba tu conexion a internet." -ForegroundColor Red
        return
    }

    # --- 3. Instalar sin preguntas ------------------------------
    # Opciones de Inno Setup: /VERYSILENT sin ventanas, /TASKS crea el icono del escritorio.
    # «finally» se ejecuta siempre, vaya bien o mal: asi el instalador descargado
    # nunca se queda olvidado en la carpeta temporal.
    Write-Host " [3/3] Instalando ..."
    try {
        $p = Start-Process $destino -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/TASKS="desktopicon"' -Wait -PassThru
    } catch {
        # Otra proteccion de Windows (por ejemplo, la de un ordenador de empresa o instituto)
        # tambien puede bloquearlo. El mensaje es el mismo.
        Show-AvisoBloqueo
        return
    } finally {
        Remove-Item $destino -ErrorAction SilentlyContinue
    }
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
