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
from tunedrop.core.downloader import build_tags, save_to_destination
from tunedrop.core.history import History
from tunedrop.core.models import AudioFormat, Track
from tunedrop.core.paths import build_output_path, sanitize, unique_path
from tunedrop.core.search import entry_to_track, is_url
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
