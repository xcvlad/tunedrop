import io
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from mutagen.id3 import ID3
from mutagen.mp4 import MP4
from PIL import Image

from tunedrop.core.converter import build_command
from tunedrop.core.downloader import build_tags, save_lrc, save_to_destination
from tunedrop.core.history import History
from tunedrop.core import updates
from tunedrop.core.lyrics import pick_best, strip_timestamps
from tunedrop.core.models import AudioFormat, Track
from tunedrop.core.paths import build_output_path, sanitize, unique_path
from tunedrop.core.search import _friendly, entry_to_track, is_url
from tunedrop.core.settings import Settings, _linux_music_dir
from tunedrop.core.tagger import Tags, prepare_cover, write_tags
from tunedrop.core.titles import clean_channel, clean_title, split_artist_title

HAS_FFMPEG = shutil.which("ffmpeg") is not None


# --- títulos -------------------------------------------------------------------

@pytest.mark.parametrize("raw, expected", [
    ("Song Name (Official Music Video)", "Song Name"),
    ("Song Name [HD]", "Song Name"),
    ("Canción (Video Oficial)", "Canción"),
    ("Song (Lyrics)", "Song"),
    ("Song - Official Video", "Song"),
    ("Song (feat. Someone)", "Song (feat. Someone)"),
    # Mezclas de relleno (antes se quedaban)
    ("Bohemian Rhapsody (Official Video Remastered)", "Bohemian Rhapsody"),
    ("Song (Official 4K Video)", "Song"),
    ("Song (Official HD Video) [Remastered 2011]", "Song"),
    ("Song (2011 Remaster)", "Song"),
    ("Song (Remasterizado 2015)", "Song"),
    ("Song (Letra/Lyrics)", "Song"),
    ("Canción (Video Oficial) (Con Letra)", "Canción"),
    ("Song 【Official Video】", "Song"),
    ("Song (Official M/V)", "Song"),
    ("SONG (OFFICIAL MUSIC VIDEO)", "SONG"),
    ("Song (Audio)", "Song"),
    # Coletillas del final
    ("Song | Official Music Video", "Song"),
    ("Song - Remastered 2011", "Song"),
    ("Song // Lyrics", "Song"),
    ("Song - Remastered 2011 - Official Video", "Song"),
    # Casos reales de YouTube
    ("Tití Me Preguntó (La Letra / Lyrics)", "Tití Me Preguntó"),
    ("Smells Like Teen Spirit (Full Version 4K Remastered 60 FPS)", "Smells Like Teen Spirit"),
    ("Titi Me Pregunto (Audio/Estudio) 2022", "Titi Me Pregunto 2022"),
    ("BAD BUNNY-TITI ME PREGUNTO HQ", "BAD BUNNY-TITI ME PREGUNTO"),
    ("Billie Jean (Live) - 1983", "Billie Jean (Live)"),
    ("Song (Radio Version)", "Song (Radio Version)"),
    # Lo que dice algo de la canción se queda
    ("Song (Live)", "Song (Live)"),
    ("Song (Remix)", "Song (Remix)"),
    ("Song (with Justin Bieber)", "Song (with Justin Bieber)"),
    ("Song (con Rosalía)", "Song (con Rosalía)"),
    ("Song (Acoustic Version)", "Song (Acoustic Version)"),
    ("Song - Live at Wembley 1986", "Song - Live at Wembley 1986"),
    ("Video Killed the Radio Star", "Video Killed the Radio Star"),
])
def test_clean_title(raw, expected):
    assert clean_title(raw) == expected


def test_split_artist_title_uses_separator():
    assert split_artist_title("Artista - Canción (Official Video)") == ("Artista", "Canción")


def test_split_artist_title_falls_back_to_channel():
    assert split_artist_title("Canción", "Artista - Topic") == ("Artista", "Canción")


def test_clean_channel():
    assert clean_channel("ArtistVEVO") == "Artist"
    assert clean_channel("Artist - Topic") == "Artist"


# --- rutas ---------------------------------------------------------------------

def test_sanitize_removes_fat32_invalid_chars():
    assert sanitize('AC/DC: "Back" <In> Black?') == "AC_DC_ _Back_ _In_ Black_"


def test_sanitize_reserved_and_trailing_dots():
    assert sanitize("CON") == "_CON"
    assert sanitize("Title...") == "Title"
    assert sanitize("") == "Sin título"


def test_build_output_path_is_flat(tmp_path):
    p = build_output_path(tmp_path, artist="Queen", title="Bohemian Rhapsody", extension="mp3")
    assert p == tmp_path / "Queen - Bohemian Rhapsody.mp3"


def test_build_output_path_cleans_names(tmp_path):
    p = build_output_path(tmp_path, artist="AC/DC", title="", extension="m4a")
    assert p == tmp_path / "AC_DC - Sin título.m4a"


def test_unique_path(tmp_path):
    f = tmp_path / "x.mp3"
    f.write_bytes(b"")
    assert unique_path(f) == tmp_path / "x (2).mp3"


def test_save_to_destination_copies_and_cleans_partial(tmp_path):
    src = tmp_path / "out.mp3"
    src.write_bytes(b"audio")
    target = tmp_path / "musica" / "A - T.mp3"
    save_to_destination(src, target)
    assert target.read_bytes() == b"audio"


@pytest.mark.skipif(sys.platform != "win32", reason="los permisos (ACL) solo existen en Windows")
def test_save_to_destination_inherits_folder_permissions(tmp_path):
    def permisos(f: Path) -> str:
        salida = subprocess.run(["icacls", str(f)], capture_output=True, text=True).stdout
        # icacls acaba con una línea de resumen tras una línea en blanco: nos quedamos
        # solo con los permisos, sin la ruta del archivo ni los espacios de alineación.
        bloque = salida.replace(str(f), "").split("\n\n")[0]
        return "\n".join(linea.strip() for linea in bloque.splitlines())

    # Carpeta de destino con un permiso extra (S-1-1-0 = «Todos»), para que se note
    # si la canción lo hereda o trae los permisos de su carpeta temporal.
    musica = tmp_path / "musica"
    musica.mkdir()
    subprocess.run(["icacls", str(musica), "/grant", "*S-1-1-0:(OI)(CI)R"], capture_output=True, check=True)

    workdir = Path(tempfile.mkdtemp())  # carpeta privada, como en download_track
    try:
        src = workdir / "out.mp3"
        src.write_bytes(b"audio")
        target = musica / "A - T.mp3"
        save_to_destination(src, target)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)

    referencia = musica / "creado_aqui.mp3"
    referencia.write_bytes(b"x")
    assert permisos(target) == permisos(referencia)


# --- búsqueda ------------------------------------------------------------------

def test_is_url():
    assert is_url("https://www.youtube.com/watch?v=abc")
    assert is_url("www.youtube.com/watch?v=abc")
    assert not is_url("daft punk one more time")


@pytest.mark.parametrize("raw, expected", [
    ("\x1b[0;31mERROR:\x1b[0m [youtube] xxxxxxxxxxx: This video is unavailable", "Ese vídeo no está disponible."),
    ("ERROR: [generic] Unsupported URL: https://example.com", "Ese enlace no es compatible."),
    ("ERROR: [youtube] abc123DEF45: Sign in to confirm your age", "Sign in to confirm your age"),
])
def test_friendly_error_messages(raw, expected):
    assert _friendly(raw) == expected


def test_entry_to_track_youtube_flat():
    entry = {"id": "aqz-KE-bpKQ", "ie_key": "Youtube", "title": "T", "channel": "C",
             "duration": 61.0, "url": "https://www.youtube.com/watch?v=aqz-KE-bpKQ",
             "thumbnails": [{"url": "small", "width": 168}, {"url": "big", "width": 336},
                            {"url": "huge", "width": 1280}]}
    t = entry_to_track(entry)
    assert t.url == "https://www.youtube.com/watch?v=aqz-KE-bpKQ"
    assert t.thumbnail == "big"
    assert t.duration_text == "1:01"


def test_build_tags_prefers_music_metadata():
    info = {"title": "Whatever (Official Video)", "track": "Real Song", "artists": ["X", "Y"],
            "album": "LP", "release_year": 2020, "track_number": 4, "webpage_url": "u"}
    tags = build_tags(info, Track(id="1", url="u", title="t"))
    assert (tags.title, tags.artist, tags.album, tags.year, tags.track_number) == \
        ("Real Song", "X, Y", "LP", "2020", 4)
    assert tags.album_artist == "X"


def test_build_tags_cleans_music_track_name():
    info = {"title": "x", "track": "Bohemian Rhapsody (Remastered 2011)", "artists": ["Queen"]}
    assert build_tags(info, Track(id="1", url="u", title="t")).title == "Bohemian Rhapsody"


def test_split_artist_title_real_example():
    assert split_artist_title("Queen – Bohemian Rhapsody (Official Video Remastered)") == \
        ("Queen", "Bohemian Rhapsody")


@pytest.mark.parametrize("raw, expected", [
    ("Bad Bunny - Tití Me Preguntó (Official Video) | Un Verano Sin Ti", ("Bad Bunny", "Tití Me Preguntó")),
    ("SHAKIRA || BZRP Music Sessions #53 (Official Video)", ("SHAKIRA", "BZRP Music Sessions #53")),
    ("@coldplay - Yellow (Lyrics)", ("coldplay", "Yellow")),
    ("Daft Punk - Get Lucky (Official Audio) ft. Pharrell Williams", ("Daft Punk", "Get Lucky ft. Pharrell Williams")),
    ("BTS (방탄소년단) 'Dynamite' Official MV", ("BTS (방탄소년단)", "Dynamite")),
    ("Numb (Official Music Video) [4K UPGRADE] – Linkin Park", ("Numb", "Linkin Park")),  # al revés: no se puede saber
    ("Guns N' Roses Patience", ("Canal", "Guns N' Roses Patience")),
])
def test_split_artist_title_youtube_cases(raw, expected):
    assert split_artist_title(raw, "Canal") == expected


def test_build_tags_from_video_title():
    info = {"title": "Artist - Song [HD]", "channel": "Uploader", "upload_date": "20190102"}
    tags = build_tags(info, Track(id="1", url="u", title="t"))
    assert (tags.artist, tags.title, tags.year, tags.album) == ("Artist", "Song", "2019", None)


# --- conversión ----------------------------------------------------------------

@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg no instalado")
def test_build_command_formats(tmp_path):
    src, dst = tmp_path / "a.webm", tmp_path / "a.mp3"
    v0 = build_command(src, dst, AudioFormat.MP3_V0, normalize=False)
    assert "-q:a" in v0 and "0" in v0 and "libmp3lame" in v0
    cbr = build_command(src, dst, AudioFormat.MP3_320, normalize=True)
    assert "320k" in cbr and any(a.startswith("loudnorm") for a in cbr)
    copy = build_command(src, tmp_path / "a.m4a", AudioFormat.M4A, normalize=False)
    assert copy[copy.index("-c:a") + 1] == "copy"
    reenc = build_command(src, tmp_path / "a.m4a", AudioFormat.M4A, normalize=False,
                          source_is_aac=False)
    assert reenc[reenc.index("-c:a") + 1] == "aac"


# --- etiquetas -----------------------------------------------------------------

def _jpeg(w, h, progressive=True) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (200, 50, 50)).save(buf, "JPEG", progressive=progressive)
    return buf.getvalue()


def test_prepare_cover_square_baseline():
    out = Image.open(io.BytesIO(prepare_cover(_jpeg(1280, 720))))
    assert out.size == (600, 600)
    assert not out.info.get("progressive") and not out.info.get("progression")


def _silence(tmp_path: Path, ext: str) -> Path:
    path = tmp_path / f"s.{ext}"
    codec = ["-c:a", "libmp3lame"] if ext == "mp3" else ["-c:a", "aac"]
    subprocess.run(["ffmpeg", "-loglevel", "error", "-f", "lavfi", "-i",
                    "anullsrc=r=44100:cl=stereo", "-t", "1", *codec, str(path)], check=True)
    return path


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg no instalado")
def test_write_id3v23_with_cover(tmp_path):
    path = _silence(tmp_path, "mp3")
    write_tags(path, Tags(title="Ñandú", artist="Artista", album="Disco", track_number=2,
                          year="2021"), prepare_cover(_jpeg(500, 500)))
    id3 = ID3(path)
    assert id3.version == (2, 3, 0)
    assert str(id3["TIT2"]) == "Ñandú"
    assert str(id3["TPE2"]) == "Artista"
    assert id3.getall("APIC")[0].mime == "image/jpeg"


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg no instalado")
def test_write_mp4_tags(tmp_path):
    path = _silence(tmp_path, "m4a")
    write_tags(path, Tags(title="T", artist="A", track_number=5), None)
    mp4 = MP4(path)
    assert mp4["\xa9nam"] == ["T"] and mp4["trkn"] == [(5, 0)]


@pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg no instalado")
def test_write_lyrics_mp3_and_m4a(tmp_path):
    letra = "Primera línea\nSegunda línea"
    mp3 = _silence(tmp_path, "mp3")
    write_tags(mp3, Tags(title="T", artist="A", lyrics=letra), None)
    assert ID3(mp3).getall("USLT")[0].text == letra
    m4a = _silence(tmp_path, "m4a")
    write_tags(m4a, Tags(title="T", artist="A", lyrics=letra), None)
    assert MP4(m4a)["\xa9lyr"] == [letra]


# --- letras (sin red: resultados de LRCLIB inventados) -------------------------

def _lrclib(duration, plain="Hola\nAdiós", synced="[00:01.00] Hola\n[00:02.50] Adiós", instrumental=False):
    return {"duration": duration, "plainLyrics": plain, "syncedLyrics": synced,
            "instrumental": instrumental}


def test_pick_best_prefers_same_duration():
    results = [_lrclib(263, plain="corta"), _lrclib(354, plain="la buena"), _lrclib(317, plain="otra")]
    assert pick_best(results, 355).plain == "la buena"


def test_pick_best_prefers_synced_among_close_durations():
    results = [_lrclib(355, plain="sin tiempos", synced=None), _lrclib(356, plain="con tiempos")]
    lyrics = pick_best(results, 355)
    assert lyrics.plain == "con tiempos" and lyrics.synced


def test_pick_best_drops_synced_if_other_version():
    # La única letra dura 40 s más: el texto sirve, los tiempos no.
    lyrics = pick_best([_lrclib(395)], 355)
    assert lyrics.plain == "Hola\nAdiós" and lyrics.synced is None


def test_pick_best_without_lyrics():
    assert pick_best([], 200) is None
    assert pick_best([_lrclib(200, plain=None, synced=None, instrumental=True)], 200) is None


def test_pick_best_plain_from_synced_only():
    lyrics = pick_best([_lrclib(200, plain=None)], 200)
    assert lyrics.plain == "Hola\nAdiós"


def test_save_lrc_next_to_song(tmp_path):
    song = tmp_path / "Artista - Canción.mp3"
    lrc = save_lrc(song, Tags(title="Canción", artist="Artista", album="Disco"), "[00:01.00] Hola")
    assert lrc.name == "Artista - Canción.lrc"
    assert lrc.read_bytes().startswith(b"\xef\xbb\xbf")   # UTF-8 con BOM
    assert lrc.read_text(encoding="utf-8-sig").splitlines() == [
        "[ar:Artista]", "[ti:Canción]", "[al:Disco]", "[00:01.00] Hola"]


# --- aviso de versión nueva (sin red: la respuesta de GitHub es inventada) -----

@pytest.mark.parametrize("latest, current, newer", [
    ("0.4.0", "0.3.0", True),
    ("0.10.0", "0.9.9", True),     # 10 > 9 (comparar como texto diría lo contrario)
    ("0.3.0", "0.3.0", False),
    ("0.2.9", "0.3.0", False),
    ("1.0", "0.9.9", True),
])
def test_is_newer(latest, current, newer):
    assert updates.is_newer(latest, current) is newer


def _github_redirige_a(monkeypatch, url):
    class Respuesta:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def geturl(self):
            return url

    monkeypatch.setattr(updates.urllib.request, "urlopen", lambda *a, **k: Respuesta())


def test_latest_version_follows_redirect(monkeypatch):
    _github_redirige_a(monkeypatch, "https://github.com/xcvlad/tunedrop/releases/tag/v0.4.0")
    assert updates.latest_version() == "0.4.0"


def test_latest_version_without_releases(monkeypatch):
    # Sin versiones publicadas, GitHub se queda en la página de releases.
    _github_redirige_a(monkeypatch, "https://github.com/xcvlad/tunedrop/releases")
    assert updates.latest_version() is None


def test_latest_version_offline(monkeypatch):
    def sin_red(*args, **kwargs):
        raise OSError("sin conexión")
    monkeypatch.setattr(updates.urllib.request, "urlopen", sin_red)
    assert updates.latest_version() is None


def test_install_kind_from_source():
    assert updates.install_kind() == "manual"   # los tests se ejecutan desde el código


def test_strip_timestamps():
    assert strip_timestamps("[00:01.00] Hola\n[01:02.345]Adiós\n[00:03] Fin") == "Hola\nAdiós\nFin"


# --- configuración e historial -------------------------------------------------

def test_settings_roundtrip(tmp_path):
    f = tmp_path / "s.json"
    s = Settings(audio_format="m4a", normalize=True)
    s.save(f)
    loaded = Settings.load(f)
    assert loaded.format is AudioFormat.M4A and loaded.normalize


def test_settings_ignores_unknown_and_bad_values(tmp_path):
    f = tmp_path / "s.json"
    f.write_text('{"audio_format": "flac", "nope": 1}', encoding="utf-8")
    assert Settings.load(f).format is AudioFormat.MP3_V0


def test_linux_music_dir_reads_user_dirs(tmp_path, monkeypatch):
    # En Linux la carpeta de música puede estar traducida: la dice ~/.config/user-dirs.dirs
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    user_dirs = tmp_path / "user-dirs.dirs"
    user_dirs.write_text('XDG_DESKTOP_DIR="$HOME/Escritorio"\nXDG_MUSIC_DIR="$HOME/Música"\n',
                         encoding="utf-8")
    assert _linux_music_dir() == Path.home() / "Música"
    user_dirs.write_text('XDG_MUSIC_DIR="$HOME/"\n', encoding="utf-8")  # sin carpeta de música
    assert _linux_music_dir() is None
    user_dirs.unlink()
    assert _linux_music_dir() is None


def test_history_requires_existing_file(tmp_path):
    h = History(tmp_path / "h.json")
    song = tmp_path / "song.mp3"
    song.write_bytes(b"x")
    h.add("youtube", "abc", song, "t")
    assert History(tmp_path / "h.json").contains("youtube", "abc")
    song.unlink()
    assert not h.contains("youtube", "abc")
