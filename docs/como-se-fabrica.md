# Cómo se fabrica el programa (Windows, Linux y NixOS)

[← Volver al README](../README.md)

Para que cualquiera pueda usar tunedrop **sin instalar Python**, lo empaquetamos en un programa de Windows (`.exe`) y en uno de Linux. Lo fabrica **GitHub automáticamente** cada vez que se publica una versión, con el script [`packaging/build.py`](../packaging/build.py). Los comandos de instalación del README descargan justo ese programa.

> **Cada sistema compila su versión.** PyInstaller mete dentro del programa el Python *del sistema donde se ejecuta*, así que el `.exe` solo se puede crear en Windows y la versión de Linux solo en Linux. Por eso GitHub usa dos servidores, uno de cada sistema.

## Qué se genera en Windows

En la carpeta `dist\` aparecen:

| Archivo | Qué es |
|---|---|
| `tunedrop\` | La app lista para usar: `tunedrop.exe` y la carpeta `_internal\` con Python, las librerías, ffmpeg y Deno. |
| `tunedrop-X.Y.Z-portable.zip` | Esa misma carpeta comprimida. Se descomprime y se usa, sin instalar nada. |
| `tunedrop-X.Y.Z-setup.exe` | Instalador clásico de Windows: crea el acceso en el menú Inicio y en el escritorio, y se desinstala desde *Configuración → Aplicaciones*. |
| `SHA256SUMS.txt` | Las «huellas digitales» de los archivos anteriores, para verificarlos. |

## Qué se genera en Linux

En la carpeta `dist/` aparecen:

| Archivo | Qué es |
|---|---|
| `tunedrop/` | La app lista para usar: el ejecutable `tunedrop` y la carpeta `_internal/` con Python, las librerías, ffmpeg y Deno. |
| `tunedrop-X.Y.Z-linux-x86_64.tar.gz` | Esa misma carpeta comprimida. Usamos `.tar.gz` y no `.zip` porque guarda los permisos de ejecución, que en Linux son imprescindibles. |
| `SHA256SUMS.txt` | Las huellas del archivo anterior. |

En Linux no hay instalador tipo `setup.exe`: se descomprime y se ejecuta `./tunedrop/tunedrop`.

## Qué hace `build.py`, paso a paso

1. **Descarga ffmpeg** en `bin/` (la versión de Windows o la de Linux, según dónde se ejecute). Usamos la [compilación LGPL de BtbN](https://github.com/BtbN/FFmpeg-Builds), hecha automáticamente a partir del código oficial de ffmpeg. La variante LGPL se puede redistribuir junto a nuestra app y sigue incluyendo el codificador MP3.
2. **Copia Deno** desde la librería `deno` que instaló pip.
3. **PyInstaller** reúne en `dist/tunedrop/` un Python propio, todas las librerías, nuestro código, ffmpeg, Deno y las licencias. Usamos el modo `--onedir` (una carpeta) en lugar de un único ejecutable gigante, porque:
   - arranca mucho más rápido;
   - los antivirus lo marcan menos por error.
4. **Comprime** la carpeta: `.zip` portable en Windows, `.tar.gz` en Linux.
5. **Solo en Windows: Inno Setup** lee la receta [`packaging/instalador.iss`](../packaging/instalador.iss) y crea el `setup.exe`. Se instala en `%LOCALAPPDATA%\Programs\tunedrop`, sin pedir permisos de administrador. Su ventana sigue el modo claro u oscuro de Windows y usa dos imágenes propias (`packaging/instalador-*.png`), dibujadas con [`crear_imagenes_instalador.py`](../packaging/crear_imagenes_instalador.py). Necesita Inno Setup 6.6 o superior.
6. **Calcula las huellas SHA-256** y las guarda en `SHA256SUMS.txt`.

Para comprobar que el programa resultante funciona sin abrir la ventana:

```
dist\tunedrop\tunedrop.exe --comprobar       # Windows (el resultado queda en tunedrop-comprobacion.txt)
dist/tunedrop/tunedrop --comprobar           # Linux (lo muestra en la terminal)
```

## Cómo lo fabrica GitHub

El archivo [`.github/workflows/release.yml`](../.github/workflows/release.yml) le dice a GitHub lo siguiente: *«cuando se publique una etiqueta de versión, coge el código y, a la vez en un servidor Windows y en uno Linux, pasa los tests, ejecuta `build.py` y comprueba que el programa funciona. Después junta todo y publícalo en una Release»*.

Todo ocurre en un servidor limpio de GitHub, con el código público y un registro visible para cualquiera. Así nadie tiene que fiarse de *tu* ordenador.

Para lanzarlo: sube el número de versión en `tunedrop/__init__.py` (por ejemplo, `__version__ = "0.2.0"`), haz commit y push, y crea una etiqueta con ese mismo número:

```
git tag v0.2.0
git push origin v0.2.0
```

En unos 10 minutos aparece la versión nueva en **Releases**, y los comandos de instalación ya la descargan.

## Y en NixOS

En NixOS no se usa nada de lo anterior. NixOS guarda las librerías en `/nix/store` y no en las carpetas de siempre (`/usr/lib`...), así que el programa de Linux que crea PyInstaller no encuentra lo que necesita.

Por eso el repositorio incluye [`flake.nix`](../flake.nix), una receta que Nix sigue para montar tunedrop **desde el código**:

1. Coge del catálogo de NixOS (*nixpkgs*) las mismas librerías que `requirements.txt`: yt-dlp, PySide6, mutagen y Pillow, más ffmpeg y Deno.
2. Copia la carpeta `tunedrop/` y crea el comando `tunedrop`, preparado para que encuentre ffmpeg, Deno y los complementos de Qt.
3. Añade el icono y el acceso del menú de aplicaciones.
4. Pasa los tests. Si alguno falla, no se instala.

No hay nada que compilar ni publicar en *Releases*: cada persona lo monta en su ordenador con `nix run` o `nix profile install`, y Nix descarga ya hechas casi todas las piezas desde su propio servidor (`cache.nixos.org`). Los comandos están en el [README](../README.md#nixos).

El archivo [`.github/workflows/nix.yml`](../.github/workflows/nix.yml) comprueba en GitHub que todo funciona: monta el paquete, ejecuta el autodiagnóstico, abre la ventana sin pantalla y prueba `nix develop`. Se ejecuta en cada subida y también **cada lunes**, porque nixpkgs cambia aunque tunedrop no cambie.

## Probarlo en tu PC (opcional)

Solo si quieres ver el programa antes de publicarlo. Con el entorno de [Para programadores](../README.md#para-programadores) preparado:

```
.venv\Scripts\python packaging\build.py      # Windows
.venv/bin/python packaging/build.py          # Linux
```

Tarda unos minutos y el resultado queda en `dist/`. En Windows, el `setup.exe` solo se crea si tienes Inno Setup (`winget install -e --id JRSoftware.InnoSetup`); sin él se crea igualmente el `.zip` portable.

## Comprobar una descarga

Para asegurarte de que el archivo que te has descargado es exactamente el que compiló GitHub:

**Opción 1: la huella SHA-256** (no necesita nada instalado). En PowerShell:

```powershell
Get-FileHash .\tunedrop-0.1.0-setup.exe -Algorithm SHA256
```

En Linux:

```bash
sha256sum tunedrop-0.1.0-linux-x86_64.tar.gz
```

Compara el resultado con la línea correspondiente de `SHA256SUMS.txt` de la Release. Si coinciden, el archivo no se ha modificado.

**Opción 2: el certificado de procedencia** (necesita [GitHub CLI](https://cli.github.com/)):

```
gh attestation verify tunedrop-0.1.0-setup.exe --repo xcvlad/tunedrop
```

Demuestra criptográficamente que el archivo se compiló con el workflow de *este* repositorio, a partir de un commit concreto.

## El aviso «Windows protegió su PC»

Windows SmartScreen avisa de cualquier programa que no esté firmado con un certificado de pago (unos cientos de euros al año) o que aún no descargue mucha gente. **No significa que tenga virus.** Para abrirlo, pulsa **Más información → Ejecutar de todas formas**. Las comprobaciones de arriba son la forma de asegurarte de que el archivo es legítimo.

## Tamaño

El instalador ocupa unos 115 MB. Casi todo son ffmpeg (~130 MB sin comprimir), Deno (~100 MB) y Qt, la librería de la interfaz. Son programas completos que la app necesita para funcionar sin depender de nada instalado en el ordenador.

[← Cómo funciona](como-funciona.md) · [Volver al README](../README.md)
