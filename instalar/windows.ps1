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
#
#  Los textos que se ven en pantalla no llevan tildes, y los dibujos (logo,
#  barra, recuadros) se crean con [char]0x.... (el número Unicode de cada
#  símbolo): así la parte que se ejecuta solo usa letras normales, y
#  PowerShell 5.1 no la puede leer mal aunque se equivoque con la codificación.
# ============================================================

function Install-Tunedrop {
    $ErrorActionPreference = "Stop"
    $ProgressPreference = "SilentlyContinue"   # la barra de progreso de PowerShell 5 hace la descarga muy lenta
    $repo = "xcvlad/tunedrop"

    # PowerShell 5.1 no activa TLS 1.2 por defecto, y GitHub lo exige.
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12

    # ========================================================
    #  Aspecto: colores, símbolos y dibujos de la terminal
    # ========================================================

    # Colores y animaciones solo si la ventana entiende los códigos ANSI
    # (Windows Terminal y la consola de Windows 10/11 sí) y el usuario no los
    # ha desactivado con la variable NO_COLOR.
    $bonito = $Host.UI.SupportsVirtualTerminal -and -not $env:NO_COLOR
    # Windows Terminal (el de Windows 11) y VS Code tienen fuentes con todos los
    # símbolos. La consola antigua usa Consolas, que no tiene ni la ruedita ni el ✔.
    $moderno = [bool]($env:WT_SESSION -or $env:TERM_PROGRAM)

    if ($bonito) {
        # Códigos ANSI: ESC + [ ... m cambia el color. 38;2;R;G;B elige un color
        # exacto (rojo, verde, azul). Son los mismos colores de la app.
        $E = [char]27
        $NORMAL = "$E[0m"
        $TENUE = "$E[2m"
        $VIOLETA = "$E[38;2;139;92;246m"
        $VERDE = "$E[38;2;52;211;153m"
        $ROJO = "$E[38;2;251;113;133m"
        $AMARILLO = "$E[38;2;251;191;36m"
        $GRIS = "$E[38;2;58;64;78m"
        $BORRAR_LINEA = "`r$E[2K"      # vuelve al principio de la línea y la borra
        # Un color para cada letra del logo, del violeta al fucsia (como el icono).
        $colores = "139;92;246", "150;89;245", "161;86;244", "172;83;243",
                   "184;79;242", "195;76;241", "206;73;240", "217;70;239" |
            ForEach-Object { "$E[1;38;2;${_}m" }
    } else {
        $NORMAL = ""; $TENUE = ""; $VIOLETA = ""; $VERDE = ""; $ROJO = ""; $AMARILLO = ""; $GRIS = ""
        $BORRAR_LINEA = ""
        $colores = "", "", "", "", "", "", "", ""
    }

    # Convierte números Unicode en texto: Simbolos 0x2714 -> "✔"
    function Simbolos { $args | ForEach-Object { [string][char]$_ } }

    $NOTA = Simbolos 0x266A                                  # ♪
    if ($moderno) {
        $BIEN = Simbolos 0x2714                              # ✔
        $MAL = Simbolos 0x2718                               # ✘
        $LLENO = Simbolos 0x2501                             # ━
        $VACIO = $LLENO
        $giro = Simbolos 0x280B 0x2819 0x2839 0x2838 0x283C 0x2834 0x2826 0x2827 0x2807 0x280F   # la ruedita
        $caja = Simbolos 0x256D 0x256E 0x2570 0x256F 0x2500 0x2502                               # ╭ ╮ ╰ ╯ ─ │
    } else {
        $BIEN = Simbolos 0x221A                              # √
        $MAL = "x"
        $LLENO = Simbolos 0x2588                             # █
        $VACIO = Simbolos 0x2591                             # ░
        $giro = "|", "/", "-", "\"
        $caja = Simbolos 0x250C 0x2510 0x2514 0x2518 0x2500 0x2502                               # ┌ ┐ └ ┘ ─ │
    }

    # El logo, dibujado con bloques. Para que el script solo tenga letras normales,
    # cada símbolo se escribe con una letra y se sustituye al mostrarlo:
    #   # = █    = = ═    | = ║    F = ╔    7 = ╗    L = ╚    J = ╝
    # (F, 7, L y J tienen la forma de la esquina que representan).
    $logo = @(
        "########7##7   ##7###7   ##7#######7######7 ######7  ######7 ######7 "
        "L==##F==J##|   ##|####7  ##|##F====J##F==##7##F==##7##F===##7##F==##7"
        "   ##|   ##|   ##|##F##7 ##|#####7  ##|  ##|######FJ##|   ##|######FJ"
        "   ##|   ##|   ##|##|L##7##|##F==J  ##|  ##|##F==##7##|   ##|##F===J "
        "   ##|   L######FJ##| L####|#######7######FJ##|  ##|L######FJ##|     "
        "   L=J    L=====J L=J  L===JL======JL=====J L=J  L=J L=====J L=J     "
    )
    $anchos = 9, 9, 10, 8, 8, 8, 9, 8     # T U N E D R O P (columnas de cada letra)

    function Show-Logo {
        try { $columnas = $Host.UI.RawUI.WindowSize.Width } catch { $columnas = 80 }
        Write-Host ""
        if ($columnas -ge 72) {
            foreach ($fila in $logo) {
                $fila = $fila.Replace("#", (Simbolos 0x2588)).Replace("=", (Simbolos 0x2550)).Replace("|", (Simbolos 0x2551))
                $fila = $fila.Replace("F", (Simbolos 0x2554)).Replace("7", (Simbolos 0x2557)).Replace("L", (Simbolos 0x255A)).Replace("J", (Simbolos 0x255D))
                $linea = "  "
                $inicio = 0
                for ($n = 0; $n -lt $anchos.Count; $n++) {
                    $linea += $colores[$n] + $fila.Substring($inicio, $anchos[$n])
                    $inicio += $anchos[$n]
                }
                Write-Host ($linea + $NORMAL)
            }
        } else {
            # Ventana estrecha: el logo grande no cabría y se descolocaría.
            Write-Host "  $($colores[0])t u n e d r o p$NORMAL"
        }
        Write-Host ""
        Write-Host "  $TENUE$NOTA  Tu musica en MP3, lista para tu reproductor o iPod$NORMAL"
        Write-Host ""
    }

    # Línea de un paso terminado:  ✔ Texto  detalle
    function Show-Hecho($texto, $detalle) {
        Write-Host "$BORRAR_LINEA  $VERDE$BIEN$NORMAL  $texto  $TENUE$detalle$NORMAL"
    }

    # Línea de un paso en marcha, con la ruedita. $i es el número de fotograma.
    function Show-Espera($texto, $i) {
        if ($bonito) { Write-Host -NoNewline "$BORRAR_LINEA  $VIOLETA$($giro[$i % $giro.Count])$NORMAL  $texto" }
    }

    function Show-Fallo($texto, $pista) {
        Write-Host "$BORRAR_LINEA  $ROJO$MAL $texto$NORMAL"
        if ($pista) { Write-Host "    $pista" }
        Write-Host ""
    }

    # Dibuja un recuadro alrededor de las líneas de texto.
    # Uso: Show-Caja $VERDE "linea 1", "linea 2"
    function Show-Caja($color, [string[]]$lineas) {
        $ancho = ($lineas | Measure-Object -Property Length -Maximum).Maximum + 4
        Write-Host ("  " + $color + $caja[0] + ($caja[4] * $ancho) + $caja[1] + $NORMAL)
        foreach ($l in $lineas) {
            Write-Host ("  " + $color + $caja[5] + $NORMAL + "  " + $l.PadRight($ancho - 4) + "  " + $color + $caja[5] + $NORMAL)
        }
        Write-Host ("  " + $color + $caja[2] + ($caja[4] * $ancho) + $caja[3] + $NORMAL)
        Write-Host ""
    }

    # Barra de descarga:  ━━━━━━━━━━━━━━━━━━  64 %  74/115 MB
    function Show-Barra($bajado, $total) {
        $mb = [math]::Floor($bajado / 1MB)
        if ($total -gt 0) {
            $llenos = [math]::Floor($bajado * 30 / $total)
            $porcentaje = "{0,3} %" -f [math]::Floor($bajado * 100 / $total)
            $barra = $VIOLETA + ($LLENO * $llenos) + $GRIS + ($VACIO * (30 - $llenos)) + $NORMAL
            Write-Host -NoNewline "$BORRAR_LINEA  $barra  $porcentaje  $TENUE$mb/$([math]::Floor($total / 1MB)) MB$NORMAL"
        } else {
            Write-Host -NoNewline "$BORRAR_LINEA  $VIOLETA$($giro[0])$NORMAL  Descargando  $TENUE$mb MB$NORMAL"
        }
    }

    # Descarga un archivo trozo a trozo para poder ir dibujando la barra.
    # (Invoke-WebRequest no deja saber cuánto lleva descargado.)
    function Save-Archivo($url, $destino) {
        $respuesta = [Net.HttpWebRequest]::Create($url).GetResponse()
        $total = $respuesta.ContentLength          # tamaño total (-1 si GitHub no lo dice)
        $entrada = $respuesta.GetResponseStream()
        $salida = [IO.File]::Create($destino)
        try {
            $trozo = New-Object byte[] 262144       # se lee de 256 KB en 256 KB
            $bajado = 0
            $reloj = [Diagnostics.Stopwatch]::StartNew()
            while (($n = $entrada.Read($trozo, 0, $trozo.Length)) -gt 0) {
                $salida.Write($trozo, 0, $n)
                $bajado += $n
                # Se redibuja unas 6 veces por segundo, no con cada trozo (sería más lento).
                if ($bonito -and $reloj.ElapsedMilliseconds -ge 150) {
                    Show-Barra $bajado $total
                    $reloj.Restart()
                }
            }
            if ($bonito) { Show-Barra $bajado $total }   # la barra al 100 %
        } finally {
            $salida.Dispose()
            $entrada.Dispose()
            $respuesta.Dispose()
        }
        return $bajado
    }

    function Show-AvisoBloqueo {
        # Smart App Control (Windows 11) solo deja ejecutar programas firmados con un
        # certificado o muy conocidos. tunedrop todavia no esta firmado, asi que lo bloquea
        # sin opcion de "ejecutar de todas formas". No hay nada que el script pueda hacer.
        Write-Host $BORRAR_LINEA -NoNewline
        Show-Caja $ROJO "$MAL  Windows no deja instalar tunedrop en este ordenador.",
            "",
            "   Lo mas probable es que tengas activado el",
            "   'Control inteligente de aplicaciones' (Smart App Control).",
            "   Es una proteccion de Windows 11 que solo permite programas",
            "   con firma digital, y tunedrop aun no la tiene.",
            "   No es un virus ni un fallo de tu ordenador.",
            "",
            "   Mas informacion:",
            "   https://github.com/xcvlad/tunedrop#smart-app-control"
    }

    # ========================================================
    #  Instalar
    # ========================================================

    # El cursor se esconde durante las animaciones para que no parpadee.
    # «finally» lo vuelve a mostrar siempre: al terminar, si hay un error o con Ctrl+C.
    try { [Console]::CursorVisible = $false } catch { }
    try {
        Show-Logo

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
        Show-Espera "Buscando la ultima version" 0
        try {
            $r = Invoke-WebRequest "https://github.com/$repo/releases/latest" -Method Head -UseBasicParsing
            if ($r.BaseResponse.ResponseUri) { $final = $r.BaseResponse.ResponseUri.AbsoluteUri }      # PowerShell 5
            else { $final = $r.BaseResponse.RequestMessage.RequestUri.AbsoluteUri }                     # PowerShell 7
        } catch {
            $final = ""
        }
        $etiqueta = $final.Split("/")[-1]
        if (-not $etiqueta.StartsWith("v")) {
            Show-Fallo "No se encontro ninguna version publicada." "Comprueba tu conexion o mira https://github.com/$repo/releases"
            return
        }
        $archivo = "tunedrop-$($etiqueta.Substring(1))-setup.exe"      # «v0.1.0» -> «tunedrop-0.1.0-setup.exe»
        Show-Hecho "Ultima version encontrada" $etiqueta

        # --- 2. Descargar ------------------------------------------
        $destino = Join-Path $env:TEMP $archivo
        try {
            $bajado = Save-Archivo "https://github.com/$repo/releases/download/$etiqueta/$archivo" $destino
        } catch {
            Remove-Item $destino -ErrorAction SilentlyContinue       # por si quedo a medias
            Show-Fallo "No se pudo descargar $archivo." "Comprueba tu conexion a internet y vuelve a intentarlo."
            return
        }
        Show-Hecho "Descargado" "$([math]::Floor($bajado / 1MB)) MB"

        # --- 3. Instalar sin preguntas ------------------------------
        # Opciones de Inno Setup: /VERYSILENT sin ventanas, /TASKS crea el icono del escritorio.
        # «finally» se ejecuta siempre, vaya bien o mal: asi el instalador descargado
        # nunca se queda olvidado en la carpeta temporal.
        try {
            $p = Start-Process $destino -ArgumentList '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/TASKS="desktopicon"' -PassThru
            $null = $p.Handle     # sin esta linea, PowerShell a veces pierde el codigo de salida
            $i = 0
            while (-not $p.HasExited) {
                Show-Espera "Instalando" $i
                $i++
                Start-Sleep -Milliseconds 100
            }
            $p.WaitForExit()
        } catch {
            # Otra proteccion de Windows (por ejemplo, la de un ordenador de empresa o instituto)
            # tambien puede bloquearlo. El mensaje es el mismo.
            Show-AvisoBloqueo
            return
        } finally {
            Remove-Item $destino -ErrorAction SilentlyContinue
        }
        if ($p.ExitCode -ne 0) {
            Show-Fallo "El instalador termino con el codigo $($p.ExitCode)."
            return
        }
        Show-Hecho "Instalado" "en el menu Inicio y en el escritorio"
        Write-Host ""

        # --- Listo -------------------------------------------------
        Show-Caja $VERDE "$BIEN  Listo: tunedrop $($etiqueta.Substring(1)) ya esta instalado.",
            "",
            "   Se abrira ahora mismo. Las proximas veces, abrelo",
            "   desde el menu Inicio o el icono del escritorio."
        $exe = Join-Path $env:LOCALAPPDATA "Programs\tunedrop\tunedrop.exe"
        if (Test-Path $exe) { Start-Process $exe }
    } finally {
        try { [Console]::CursorVisible = $true } catch { }
    }
}

Install-Tunedrop
