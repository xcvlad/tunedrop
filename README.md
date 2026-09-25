<p align="center">
  <img src="tunedrop/assets/icono.png" width="96" alt="icono de tunedrop">
</p>

<h1 align="center">tunedrop</h1>

<p align="center">
  <b>Busca tus canciones, márcalas y descárgalas de una vez en MP3,<br>
  con título, artista y carátula, listas para tu reproductor MP3 o iPod.</b>
</p>

<p align="center">
  <a href="#instalar"><b>⬇ Instalar en Windows y Linux</b></a> ·
  <a href="docs/como-funciona.md">Cómo funciona</a> ·
  <a href="#para-programadores">Para programadores</a>
</p>

![Captura de tunedrop](docs/img/captura.png)

> Proyecto de estudiante de **ASIR**, de código abierto. Todo el código está en este repositorio, y el programa descargable se compila de forma pública y automática a partir de él (ver [¿Es fiable?](#es-fiable)).

---

## Qué hace

- 🔎 **Busca** canciones escribiendo su nombre, o pega un enlace de YouTube, una playlist, SoundCloud, Bandcamp…
- ➕ **Elige** las que quieras con un clic, o **Añadir todas** para una playlist entera.
- ⬇ **Descarga** todas de una vez, con varias en paralelo y el progreso de cada una.
- 🎵 **Archivos listos para reproductores e iPods**:
  - Etiquetas de título, artista, álbum y año.
  - Carátula incrustada.
  - Todas las canciones juntas en una carpeta, con nombres ordenados: `Artista - Título.mp3`.
  - Títulos limpios, sin «(Official Video)».
- 🎚 **Calidad a elegir**: MP3 V0 (recomendado), MP3 320 kbps o M4A original sin pérdidas extra.

## Instalar

Se instala con **un solo comando**. No necesitas Python ni nada más: el comando descarga la última versión y la instala como cualquier app, solo para tu usuario y sin permisos de administrador. Para actualizar, vuelve a ejecutarlo.

### Windows

1. Abre **PowerShell**: pulsa el menú Inicio, escribe `PowerShell` y pulsa Intro.
2. Copia esta línea, pégala en la ventana azul y pulsa Intro:
   ```powershell
   irm https://raw.githubusercontent.com/xcvlad/tunedrop/main/instalar/windows.ps1 | iex
   ```
3. Espera a que diga **Listo**. tunedrop aparece en el menú Inicio y en el escritorio.

Para desinstalarlo: *Configuración → Aplicaciones → tunedrop → Desinstalar*.

### Linux

1. Abre una terminal.
2. Copia esta línea, pégala y pulsa Intro:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/xcvlad/tunedrop/main/instalar/linux.sh | bash
   ```
3. Espera a que diga **Listo**. tunedrop aparece en el menú de aplicaciones, y también se abre escribiendo `tunedrop`.

Para desinstalarlo:
```bash
curl -fsSL https://raw.githubusercontent.com/xcvlad/tunedrop/main/instalar/linux.sh | bash -s -- --desinstalar
```

> Si la ventana no se abre y ves un error sobre `xcb`, instala la librería que Qt necesita: `sudo apt install libxcb-cursor0` (Ubuntu/Debian), `sudo dnf install xcb-util-cursor` (Fedora) o `sudo pacman -S xcb-util-cursor` (Arch). El instalador ya te avisa si te falta.

### Cómo se usa

1. Abre tunedrop, escribe el nombre de una canción y pulsa **Buscar**.
2. Pulsa **+** en las que quieras.
3. Pulsa **Descargar**. Las canciones aparecen en tu carpeta de música, dentro de `tunedrop`, con el nombre `Artista - Título.mp3`.

> Pegar en la terminal un comando de internet es cómodo, pero solo debes hacerlo si confías en quien lo publica. Puedes leer antes lo que hace cada script: [`instalar/windows.ps1`](instalar/windows.ps1) y [`instalar/linux.sh`](instalar/linux.sh). Y si quieres comprobar que el programa descargado es legítimo, mira [¿Es fiable?](#es-fiable).

## Para programadores

Si quieres ver o cambiar el código y abrir la app sin instalarla, necesitas [Python](https://www.python.org/downloads/) 3.10 o superior. Dentro de la carpeta del proyecto:

**Windows**
```
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
.venv\Scripts\python packaging\descargar_ffmpeg.py
.venv\Scripts\python -m tunedrop
```

**Linux**
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python packaging/descargar_ffmpeg.py
.venv/bin/python -m tunedrop
```

Qué hace cada línea:
1. Crea `.venv`, una carpeta con las librerías de este proyecto, separada del resto del sistema.
2. Instala las librerías de la app y las herramientas para tests y compilar.
3. Descarga ffmpeg en `bin/` (si ya lo tienes instalado en el sistema, puedes saltarte este paso).
4. Abre la app.

Para pasar los tests: `.venv\Scripts\python -m pytest` (Linux: `.venv/bin/python -m pytest`).

## Documentación

| Guía | Para qué |
|---|---|
| [Cómo funciona](docs/como-funciona.md) | Qué es cada archivo, cómo funciona la app por dentro y un glosario de palabras técnicas. |
| [Cómo se fabrica el programa](docs/como-se-fabrica.md) | Cómo GitHub crea el programa de Windows y Linux, y cómo comprobar que una descarga es legítima. |

## ¿Es fiable?

- **Todo el código es abierto**: está en este repositorio y cualquiera puede leerlo.
- **El programa no se compila en el ordenador de nadie**: lo compila GitHub Actions a partir de este código, con el script [`packaging/build.py`](packaging/build.py). El registro completo de cada compilación es público en la pestaña **Actions**.
- **Cada descarga se puede verificar**: las Releases incluyen `SHA256SUMS.txt` y un certificado de procedencia (*attestation*) que demuestra que el archivo salió de este repositorio. Cómo se comprueba: [ver guía](docs/como-se-fabrica.md#comprobar-una-descarga).
- **Sin servidores intermedios, anuncios ni telemetría**: la app se conecta directamente desde tu ordenador a YouTube o a la web que elijas. No envía datos a ningún otro sitio.

## Sobre la calidad del audio

YouTube guarda el audio a unos **128-160 kbps** (formatos Opus o AAC). Convertirlo a «MP3 320» no mejora el sonido; solo ocupa más espacio. Por eso:

- **MP3 V0** (por defecto) conserva todo lo que trae el original, con un buen tamaño y compatible con cualquier reproductor.
- **M4A** copia el audio original **tal cual**, sin volver a comprimirlo. El iPod lo lee de forma nativa.
- La app te muestra la **calidad real de origen** de cada canción.

## Hecho con

| Pieza | Qué hace | Licencia |
|---|---|---|
| [Python](https://www.python.org/) | Lenguaje de programación | PSF |
| [PySide6 (Qt)](https://doc.qt.io/qtforpython-6/) | Interfaz gráfica | LGPL-3.0 |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Conexión con YouTube y otras webs | Unlicense |
| [Deno](https://deno.com/) | Ejecuta el JavaScript que YouTube exige | MIT |
| [ffmpeg](https://ffmpeg.org/) ([compilación LGPL](https://github.com/BtbN/FFmpeg-Builds)) | Conversión a MP3 | LGPL-2.1+ |
| [mutagen](https://github.com/quodlibet/mutagen) | Etiquetas y carátula | GPL-2.0+ |
| [Pillow](https://python-pillow.org/) | Preparar la carátula | MIT-CMU |
| [PyInstaller](https://pyinstaller.org/) · [Inno Setup](https://jrsoftware.org/isinfo.php) | Crear el programa y el instalador de Windows | GPL con excepción · propia |

## Aviso legal

tunedrop es una herramienta para descargar contenido **del que tengas derechos**, con licencia libre (Creative Commons, dominio público) o para uso personal donde la ley de tu país lo permita. Las condiciones de uso de YouTube restringen la descarga de contenido, así que el uso que hagas es responsabilidad tuya. tunedrop no elude ningún sistema anticopia (DRM).

## Licencia

El código de tunedrop tiene licencia [MIT](LICENSE): puedes usarlo, copiarlo y modificarlo libremente, siempre que mantengas el aviso de copyright.

El programa descargable (Windows y Linux) incluye librerías con otras licencias (tabla de arriba). Como mutagen es GPL, el programa compilado en su conjunto se distribuye bajo las condiciones de la GPL. Esto se cumple porque todo su código fuente es público. Las licencias van incluidas en la carpeta `_internal/licencias` del programa.
