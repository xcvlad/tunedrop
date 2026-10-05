"""Preparación común a todos los tests (pytest la carga sola)."""

import pytest

from tunedrop import idioma


@pytest.fixture(autouse=True)
def en_espanol():
    """Los tests comprueban los textos en español, sea cual sea el idioma del
    ordenador (los de GitHub Actions están en inglés)."""
    idioma.elegir("es")
    yield
    idioma.elegir("es")
