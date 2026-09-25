; ============================================================
;  Guion de Inno Setup: convierte dist\tunedrop\ en un instalador
;  normal de Windows (tunedrop-X.Y.Z-setup.exe).
;  Lo ejecuta packaging\build.py; no hace falta abrirlo a mano.
;  Documentación de Inno Setup: https://jrsoftware.org/ishelp/
; ============================================================

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif

; El modo oscuro automático (WizardStyle=... dynamic) llegó en Inno Setup 6.6.
; Con una versión más antigua, mejor un error claro que uno raro.
#if Ver < EncodeVer(6, 6, 0)
  #error Hace falta Inno Setup 6.6 o superior. Actualízalo con: winget upgrade JRSoftware.InnoSetup
#endif

[Setup]
; Identificador único de la app (no cambiarlo nunca: sirve para actualizar/desinstalar).
AppId={{6F1C2B8E-4D3A-4B8F-9E21-7A5C0D9B3E14}
AppName=tunedrop
AppVersion={#MyAppVersion}
AppPublisher=xcvlad
AppPublisherURL=https://github.com/xcvlad/tunedrop
AppSupportURL=https://github.com/xcvlad/tunedrop/issues
; Se instala solo para el usuario actual: no pide permisos de administrador.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\Programs\tunedrop
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
SetupIconFile=icono.ico
UninstallDisplayIcon={app}\tunedrop.exe
OutputDir=..\dist
OutputBaseFilename=tunedrop-{#MyAppVersion}-setup
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; --- Aspecto de las ventanas ---------------------------------
; «modern» es el diseño actual de Inno Setup, y «dynamic» hace que el
; instalador salga en modo claro u oscuro según lo tengas en Windows.
WizardStyle=modern dynamic
; Las imágenes las dibuja packaging\crear_imagenes.py.
; Lateral: franja de la izquierda en la bienvenida y al terminar.
WizardImageFile=instalador-lateral.png
; Icono: esquina de arriba a la derecha en el resto de pantallas (fondo
; transparente, así queda bien tanto en modo claro como en oscuro).
WizardSmallImageFile=instalador-icono.png
; Inno Setup se salta la pantalla de bienvenida si no se le dice lo contrario.
DisableWelcomePage=no

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

[Messages]
; Textos propios en vez de los genéricos de Inno Setup. «%n» es un salto de línea.
es.WelcomeLabel1=Te damos la bienvenida a tunedrop
es.WelcomeLabel2=Busca tus canciones, márcalas y descárgalas de una vez en MP3, con título, artista y carátula, listas para tu reproductor MP3 o iPod.%n%nSe instalará la versión {#MyAppVersion} solo para tu usuario. No hacen falta permisos de administrador.
es.FinishedHeadingLabel=¡tunedrop está listo!
es.FinishedLabel=Ya puedes abrir tunedrop desde el menú Inicio.%n%nTu música se guardará en la carpeta Música, dentro de «tunedrop».
en.WelcomeLabel1=Welcome to tunedrop
en.WelcomeLabel2=Search for your songs, pick them and download them all at once as MP3, with title, artist and cover art, ready for your MP3 player or iPod.%n%nVersion {#MyAppVersion} will be installed for your user only. No administrator rights needed.
en.FinishedHeadingLabel=tunedrop is ready!
en.FinishedLabel=You can now open tunedrop from the Start menu.%n%nYour music will be saved in your Music folder, inside "tunedrop".

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Copia toda la carpeta que creó PyInstaller.
Source: "..\dist\tunedrop\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\tunedrop"; Filename: "{app}\tunedrop.exe"
Name: "{autodesktop}\tunedrop"; Filename: "{app}\tunedrop.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\tunedrop.exe"; Description: "{cm:LaunchProgram,tunedrop}"; Flags: nowait postinstall skipifsilent
