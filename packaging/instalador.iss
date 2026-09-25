; ============================================================
;  Guion de Inno Setup: convierte dist\tunedrop\ en un instalador
;  normal de Windows (tunedrop-X.Y.Z-setup.exe).
;  Lo ejecuta packaging\build.py; no hace falta abrirlo a mano.
;  Documentación de Inno Setup: https://jrsoftware.org/ishelp/
; ============================================================

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
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
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"

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
