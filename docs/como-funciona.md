# Cómo funciona tunedrop

[← Volver al README](../README.md)

Esta guía explica **qué es cada archivo**, **cómo funciona la app por dentro** y qué significa cada palabra técnica. No hace falta saber programar para seguirla.

## El mapa del repositorio

```
tunedrop/
│
├── instalar/                 ← INSTALAR CON UN COMANDO (para quien solo quiere usar la app)
│   ├── windows.ps1           ←   Descarga el instalador de la última Release y lo ejecuta
│   └── linux.sh              ←   Descarga la versión de Linux y la añade al menú
│
├── flake.nix                 ← RECETA PARA NIXOS: cómo monta Nix la app desde el código
├── flake.lock                ←   Qué versión exacta de NixOS (nixpkgs) usa esa receta
│
├── README.md                 ← La portada del proyecto en GitHub
├── LICENSE                   ← La licencia (MIT): qué se puede hacer con el código
├── requirements.txt          ← Lista de librerías que necesita la app
├── requirements-dev.txt      ← Librerías extra para tests y para crear el programa
│
├── tunedrop/                 ← EL CÓDIGO DE LA APP
│   ├── __init__.py           ←   Nombre y versión de la app
│   ├── __main__.py           ←   Punto de arranque (abre la ventana)
│   ├── comprobar.py          ←   Autodiagnóstico: tunedrop.exe --comprobar
│   ├── assets/icono.png      ←   Icono de la ventana
│   │
│   ├── core/                 ←   El «motor»: hace el trabajo, sin ventanas
│   │   ├── search.py         ←     Buscar canciones y leer enlaces/playlists
│   │   ├── downloader.py     ←     Descarga completa de una canción (orquesta todo)
│   │   ├── converter.py      ←     Convierte el audio a MP3/M4A con ffmpeg
│   │   ├── tagger.py         ←     Escribe título, artista, carátula… en el archivo
│   │   ├── titles.py         ←     Limpia títulos: quita «(Official Video)», etc.
│   │   ├── paths.py          ←     Nombre de cada archivo: «Artista - Título.mp3»
│   │   ├── models.py         ←     Qué es una «canción» (Track) y los formatos
│   │   ├── settings.py       ←     Guarda tus ajustes
│   │   ├── history.py        ←     Recuerda qué has descargado ya
│   │   └── runtime.py        ←     Encuentra ffmpeg y Deno en el ordenador
│   │
│   └── ui/                   ←   La interfaz: todo lo que ves
│       ├── main_window.py    ←     La ventana principal
│       ├── widgets.py        ←     Las tarjetas de cada canción
│       ├── settings_dialog.py←     La ventana de ajustes (⚙)
│       ├── workers.py        ←     Trabajo en segundo plano (la ventana no se congela)
│       ├── theme.py          ←     Colores y estilo (tema oscuro)
│       └── icons.py          ←     Iconos dibujados con código (SVG)
│
├── tests/test_core.py        ← Pruebas automáticas del motor
│
├── packaging/                ← CÓMO SE CREA EL PROGRAMA (Windows y Linux)
│   ├── build.py              ←   Script que lo hace todo, paso a paso
│   ├── lanzador.py           ←   Arranque del .exe
│   ├── instalador.iss        ←   Receta del instalador (Inno Setup)
│   ├── instalador-*.png      ←   Imágenes de la ventana del instalador
│   ├── pantalla-carga.png    ←   Lo primero que sale al abrir el programa («Abriendo tunedrop…»)
│   ├── crear_imagenes.py     ←   Dibuja esas imágenes (solo para cambiar el diseño)
│   ├── descargar_ffmpeg.py   ←   Descarga ffmpeg en bin/
│   └── icono.ico             ←   Icono del .exe
│
├── .github/workflows/        ← AUTOMATIZACIÓN EN GITHUB
│   ├── tests.yml             ←   Pasa los tests en Windows y Linux en cada subida
│   ├── nix.yml               ←   Comprueba que flake.nix funciona (en cada subida y cada lunes)
│   └── release.yml           ←   Compila y publica las dos versiones al crear una versión
│
├── docs/                     ← Estas guías y la captura del README
│
├── .gitignore                ← Qué archivos NO se suben a GitHub
└── .gitattributes            ← Cómo guarda git los saltos de línea
```

Carpetas que **aparecen en tu ordenador pero no se suben** a GitHub (están en `.gitignore`):

| Carpeta | Qué es | Por qué no se sube |
|---|---|---|
| `.venv/` | El entorno virtual con las librerías | Cada programador lo crea en su PC (ver [Para programadores](../README.md#para-programadores)) |
| `bin/` | `ffmpeg` y `deno` (con `.exe` en Windows) | Pesan cientos de MB y se descargan solos |
| `build/`, `dist/` | Resultado de crear el programa | Se publica en *Releases*, no en el código |
| `result` | Lo que crea Nix al ejecutar `nix build` | Es solo un enlace al programa montado |

## Cómo funciona por dentro

Esto es lo que pasa cuando buscas y descargas una canción:

```
 TÚ                        LA APP                                   INTERNET
 ──                        ──────                                   ────────
 Escribes "canción"  ──►   search.py pide los resultados  ──────►   YouTube
                           (con yt-dlp, directamente)       ◄────   lista de vídeos
 Ves las tarjetas    ◄──   main_window.py las dibuja

 Pulsas + y Descargar ──►  downloader.py, por cada canción:
                            1. yt-dlp descarga el mejor audio ◄───  YouTube
                               (Deno resuelve el JavaScript de YouTube)
                            2. converter.py: ffmpeg lo pasa a MP3
                            3. tagger.py: pone título, artista, carátula
                            4. paths.py: lo guarda como «Artista - Título.mp3»
 Ves "Listo ✓"       ◄──   workers.py avisa a la ventana
```

La idea clave es que **el motor (`core/`) no sabe nada de ventanas**. La interfaz (`ui/`) solo le pide cosas y muestra los resultados. Así el motor se puede probar con tests y reutilizar, por ejemplo en `comprobar.py`, que funciona sin ventana.

### ¿Por qué no nos conectamos a YouTube «a mano»?

YouTube protege sus vídeos con varias capas:
- Cifra las direcciones con JavaScript que cambia a menudo.
- Pide unos tokens de verificación («PO tokens»).
- Cambia su forma de enviar el vídeo (SABR).

Mantener eso uno mismo es un trabajo a tiempo completo. [yt-dlp](https://github.com/yt-dlp/yt-dlp) es un proyecto de código abierto con cientos de colaboradores que lo mantiene al día.

Aun así, **la conexión es directa**: yt-dlp funciona *dentro* de tunedrop, en tu ordenador. No hay ninguna web ni servidor de terceros por medio.

### ¿Por qué ID3v2.3, JPEG «baseline» y nombres «FAT32»?

- Los iPods y muchos reproductores MP3 **no leen bien** las etiquetas ID3v2.4 (las más nuevas). Por eso usamos la versión 2.3.
- Los iPods clásicos **no muestran** las carátulas en JPEG «progresivo». Por eso las guardamos en JPEG «baseline», cuadradas y de 600 px.
- La memoria de un reproductor suele usar el sistema de archivos **FAT32**, que no admite caracteres como `: ? * "`. `paths.py` los sustituye.

## Glosario

| Palabra | Qué significa |
|---|---|
| **Python** | El lenguaje de programación de la app. |
| **Librería / dependencia** | Código hecho por otros que usamos (yt-dlp, PySide6…). Están en `requirements.txt`. |
| **pip** | El programa que instala librerías de Python. |
| **Entorno virtual (`.venv`)** | Una carpeta con las librerías de *este* proyecto, separada del resto del sistema. Si la borras, no se rompe nada: se vuelve a crear con `python -m venv .venv`. |
| **yt-dlp** | Librería que sabe extraer audio y vídeo de YouTube y de más de 1000 webs. |
| **ffmpeg** | Programa que convierte audio y vídeo entre formatos. |
| **Deno** | Motor de JavaScript. yt-dlp lo usa para resolver el cifrado de YouTube. |
| **PySide6 / Qt** | Herramienta para crear ventanas, botones y listas. |
| **Etiquetas ID3** | Datos guardados dentro del MP3: título, artista, carátula… |
| **kbps** | Kilobits por segundo: cuánta información de audio hay por segundo. Más no siempre significa mejor, si el original ya era más bajo. |
| **VBR / CBR** | Tasa variable (usa más bits solo donde hace falta) o tasa fija. |
| **PyInstaller** | Empaqueta Python y la app en un programa (`.exe` en Windows) que funciona sin instalar Python. |
| **Inno Setup** | Crea el instalador (`setup.exe`) de Windows. |
| **NixOS / Nix** | NixOS es una distribución de Linux en la que todo el sistema se describe en archivos de configuración. Nix es su gestor de paquetes, y también funciona en otros Linux. |
| **Flake** | Un proyecto de Nix: dice de dónde salen las piezas (*inputs*) y qué se puede construir (*outputs*). El nuestro es `flake.nix`. |
| **nixpkgs** | El catálogo oficial de paquetes de NixOS. De ahí salen Python, Qt, yt-dlp, ffmpeg y Deno cuando se usa `flake.nix`. |
| **Códigos ANSI** | Secuencias especiales que una terminal entiende como «cambia de color» o «borra esta línea». Los usan los comandos de instalar para los colores y la barra de progreso. |
| **git** | Programa que guarda el historial de cambios del código. |
| **GitHub** | Web donde se publica el repositorio git. |
| **Commit** | Una «foto» guardada del proyecto con un mensaje que explica qué cambió. |
| **Release** | Una versión publicada en GitHub con archivos descargables (el `.exe`). |
| **GitHub Actions** | Servidores de GitHub que ejecutan tareas automáticas (tests, compilar). |
| **SHA-256** | «Huella digital» de un archivo. Si cambia un solo byte, la huella es totalmente distinta. |

[Siguiente: cómo se fabrica el programa →](como-se-fabrica.md)
