import ast
import string
import sys
from pathlib import Path

import pytest

from tunedrop import idioma
from tunedrop.core.downloader import Stage
from tunedrop.core.search import _friendly
from tunedrop.idioma import INGLES, tr

CODIGO = Path(__file__).resolve().parents[1] / "tunedrop"


def _llamadas_a_tr():
    """Todas las llamadas a tr() del código: (archivo, línea, primer argumento)."""
    for archivo in sorted(CODIGO.rglob("*.py")):
        arbol = ast.parse(archivo.read_text(encoding="utf-8"))
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.Call) and getattr(nodo.func, "id", None) == "tr" and nodo.args:
                yield archivo.name, nodo.lineno, nodo.args[0]


def _huecos(texto: str) -> set[str]:
    """Los {nombres} de un texto: «Hay {n} descargas» -> {"n"}."""
    return {nombre for _, nombre, _, _ in string.Formatter().parse(texto) if nombre}


def test_todos_los_textos_traducidos():
    sin_traducir = []
    for archivo, linea, arg in _llamadas_a_tr():
        if isinstance(arg, ast.Constant):
            if arg.value not in INGLES:
                sin_traducir.append(f"{archivo}:{linea}: {arg.value!r}")
        else:
            # tr() con algo que no es un texto escrito tal cual (una f-string, una
            # variable…) no se puede comprobar. Solo se permite con las etapas
            # de descarga, que se comprueban en el test de abajo.
            assert ast.unparse(arg).endswith("stage.value"), f"{archivo}:{linea}: tr({ast.unparse(arg)})"
    assert not sin_traducir, "Faltan en idioma.INGLES:\n" + "\n".join(sin_traducir)


def test_etapas_de_descarga_traducidas():
    for stage in Stage:
        assert stage.value in INGLES


def test_traducciones_con_los_mismos_huecos():
    # Si el inglés pierde un {n} o lo escribe distinto, el texto saldría mal (o fallaría).
    for es, en in INGLES.items():
        assert _huecos(es) == _huecos(en), es


def test_tr():
    assert tr("Buscar") == "Buscar"
    assert tr("Hay {n} descargas en curso. ¿Salir y cancelarlas?", n=2).startswith("Hay 2 ")
    idioma.elegir("en")
    assert tr("Buscar") == "Search"
    assert tr("{n} canciones", n=3) == "3 songs"
    assert tr("Un texto sin traducir") == "Un texto sin traducir"   # sale en español
    assert tr("Buscar", idioma="es") == "Buscar"                    # un idioma concreto
    assert _friendly("ERROR: [youtube] abc: Private video") == "That video is private."


def test_idioma_guardado(tmp_path, monkeypatch):
    archivo = tmp_path / "idioma.txt"
    monkeypatch.setattr(idioma, "archivo", lambda: archivo)
    assert idioma.idioma_guardado() is None
    idioma.guardar_idioma("en")
    assert idioma.idioma_guardado() == "en"
    # Lo escriben también los instaladores: puede llevar BOM (PowerShell), un
    # salto de línea al final o mayúsculas.
    archivo.write_bytes(b"\xef\xbb\xbfES\r\n")
    assert idioma.idioma_guardado() == "es"
    archivo.write_text("fr", encoding="utf-8")
    assert idioma.idioma_guardado() is None


@pytest.mark.skipif(sys.platform == "win32", reason="en Windows se pregunta al sistema, no a variables")
@pytest.mark.parametrize("valor, esperado", [
    ("es_ES.UTF-8", "es"), ("es_MX.UTF-8", "es"), ("en_US.UTF-8", "en"), ("de_DE.UTF-8", "en"), ("C", "en"),
])
def test_idioma_del_sistema(monkeypatch, valor, esperado):
    for variable in ("LANGUAGE", "LC_ALL", "LC_MESSAGES"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("LANG", valor)
    assert idioma.idioma_del_sistema() == esperado
