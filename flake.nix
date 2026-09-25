# ============================================================
#  tunedrop para NixOS (y cualquier Linux con Nix).
#
#  NixOS no guarda las librerías en las carpetas de siempre (/usr/lib...),
#  así que el programa ya compilado de las Releases no funciona allí.
#  Este archivo le explica a Nix cómo montar tunedrop desde el código,
#  usando las librerías de NixOS (Python, Qt, yt-dlp, ffmpeg, Deno...).
#
#  Probarlo sin instalar nada:
#      nix run github:xcvlad/tunedrop
#
#  Instalarlo para siempre: ver la sección de NixOS del README.
#
#  Palabras de Nix que aparecen aquí:
#  - flake: un proyecto de Nix con entradas (inputs) y salidas (outputs).
#  - nixpkgs: el catálogo oficial de paquetes de NixOS.
#  - derivación: la receta para construir un paquete.
# ============================================================
{
  description = "tunedrop: descarga música en MP3 con título, artista y carátula, lista para tu MP3 o iPod";

  # De dónde salen las piezas: la rama «nixos-unstable» de nixpkgs.
  # Es la que antes recibe las versiones nuevas de yt-dlp, y yt-dlp tiene que
  # estar al día porque YouTube cambia cada pocas semanas.
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs }:
    let
      lib = nixpkgs.lib;

      # PCs normales (x86_64) y placas ARM de 64 bits, como la Raspberry Pi.
      sistemas = [ "x86_64-linux" "aarch64-linux" ];
      paraCadaSistema = f: lib.genAttrs sistemas (sistema: f nixpkgs.legacyPackages.${sistema});

      # La versión se lee de tunedrop/__init__.py, así solo se escribe en un sitio.
      version =
        let
          lineas = lib.splitString "\n" (builtins.readFile ./tunedrop/__init__.py);
          encontradas = lib.filter (x: x != null) (map (builtins.match ''__version__ = "(.*)"'') lineas);
        in
        builtins.head (builtins.head encontradas);

      # La receta del paquete.
      receta = pkgs:
        let
          py = pkgs.python3Packages;
        in
        py.buildPythonApplication {
          pname = "tunedrop";
          inherit version;

          # Solo el código de la app y los tests (no hace falta nada más).
          src = lib.fileset.toSource {
            root = ./.;
            fileset = lib.fileset.unions [ ./tunedrop ./tests ];
          };

          # No hay pyproject.toml (a propósito): la instalación se hace a mano abajo.
          pyproject = false;

          # Las librerías de requirements.txt, pero sacadas de nixpkgs.
          # (El paquete «deno» de pip no hace falta: Deno se añade al PATH más abajo.)
          dependencies = with py; [ yt-dlp pyside6 mutagen pillow ];

          nativeBuildInputs = [
            pkgs.qt6.wrapQtAppsHook      # le dice a Qt dónde están sus complementos
            pkgs.copyDesktopItems        # instala el acceso del menú de aplicaciones
          ];
          buildInputs = [
            pkgs.qt6.qtbase
            pkgs.qt6.qtwayland           # para escritorios con Wayland (GNOME, KDE...)
          ];

          installPhase = ''
            runHook preInstall

            # 1. El código de la app, donde Python busca las librerías.
            mkdir -p $out/${py.python.sitePackages}
            cp -r tunedrop $out/${py.python.sitePackages}/

            # 2. El comando «tunedrop».
            mkdir -p $out/bin
            cat > $out/bin/tunedrop <<EOF
            #!${py.python.interpreter}
            import sys
            from tunedrop.__main__ import main
            sys.exit(main())
            EOF
            chmod +x $out/bin/tunedrop

            # 3. El icono, en la carpeta estándar de iconos de Linux.
            install -Dm644 tunedrop/assets/icono.png $out/share/icons/hicolor/256x256/apps/tunedrop.png

            runHook postInstall
          '';

          # El acceso directo del menú (el mismo que crea instalar/linux.sh).
          desktopItems = [
            (pkgs.makeDesktopItem {
              name = "tunedrop";
              desktopName = "tunedrop";
              comment = "Descarga música en MP3 con título, artista y carátula";
              exec = "tunedrop";
              icon = "tunedrop";
              categories = [ "AudioVideo" "Audio" ];
              startupWMClass = "tunedrop";
            })
          ];

          # Al abrir tunedrop, ffmpeg y Deno tienen que estar en el PATH (la lista
          # de carpetas donde se buscan programas): la app los busca allí.
          dontWrapQtApps = true;
          preFixup = ''
            makeWrapperArgs+=(
              "''${qtWrapperArgs[@]}"
              --prefix PATH : ${lib.makeBinPath [ pkgs.ffmpeg-headless pkgs.deno ]}
            )
          '';

          # Antes de terminar, Nix pasa los tests (los mismos que en GitHub Actions).
          nativeCheckInputs = [ py.pytestCheckHook pkgs.ffmpeg-headless ];
          preCheck = ''
            export HOME=$(mktemp -d)
          '';

          meta = {
            description = "Descarga música en MP3 con título, artista y carátula";
            homepage = "https://github.com/xcvlad/tunedrop";
            license = lib.licenses.mit;
            mainProgram = "tunedrop";
            platforms = sistemas;
          };
        };
    in
    {
      # «nix build» y «nix run» usan este paquete.
      packages = paraCadaSistema (pkgs: rec {
        tunedrop = receta pkgs;
        default = tunedrop;
      });

      # «nix develop»: entorno para programar en NixOS (en vez de .venv, que
      # allí no funciona porque las librerías de pip no encuentran las del sistema).
      devShells = paraCadaSistema (pkgs: {
        default = pkgs.mkShell {
          packages = [
            (pkgs.python3.withPackages (py: with py; [ yt-dlp pyside6 mutagen pillow pytest ]))
            pkgs.ffmpeg-headless
            pkgs.deno
          ];
        };
      });
    };
}
