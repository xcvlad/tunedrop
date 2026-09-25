from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class AudioFormat(str, Enum):
    """Formatos de salida. El valor es lo que se guarda en la configuración."""

    MP3_V0 = "mp3_v0"
    MP3_320 = "mp3_320"
    M4A = "m4a"

    @property
    def label(self) -> str:
        return {
            AudioFormat.MP3_V0: "MP3 V0 (~245 kbps VBR) · recomendado",
            AudioFormat.MP3_320: "MP3 320 kbps CBR",
            AudioFormat.M4A: "M4A/AAC original · sin recodificar",
        }[self]

    @property
    def extension(self) -> str:
        return "m4a" if self is AudioFormat.M4A else "mp3"


@dataclass
class Track:
    """Una canción encontrada en una búsqueda o enlace, todavía sin descargar."""

    id: str
    url: str
    title: str
    channel: str = ""
    duration: int | None = None  # segundos
    thumbnail: str | None = None
    source: str = "youtube"

    # Metadatos musicales (se rellenan al descargar si el origen los tiene).
    artist: str | None = None
    album: str | None = None
    track_number: int | None = None
    year: str | None = None
    extra: dict = field(default_factory=dict, repr=False)

    @property
    def duration_text(self) -> str:
        if not self.duration:
            return "--:--"
        m, s = divmod(int(self.duration), 60)
        h, m = divmod(m, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
