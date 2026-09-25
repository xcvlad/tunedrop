"""Dibuja las dos imágenes del instalador de Windows (Inno Setup).

- instalador-lateral.png: la franja de la izquierda de las pantallas de
  bienvenida y final. Degradado del icono, la nota musical, el nombre y unas
  barras de ecualizador de adorno.
- instalador-icono.png: el cuadradito de arriba a la derecha del resto de
  pantallas (el icono de la app con fondo transparente).

Las imágenes ya están creadas en packaging/: este script solo hace falta si
quieres cambiar el diseño. Uso:  python packaging/crear_imagenes_instalador.py

Se dibujan al tamaño que Inno Setup usa con el zoom de pantalla al 250 %
(534x1022 y 159x159). En pantallas normales las reduce él solo, así que se
ven nítidas en cualquier monitor.
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

PACKAGING = Path(__file__).resolve().parent
ICONO = PACKAGING.parent / "tunedrop" / "assets" / "icono.png"

ANCHO, ALTO = 534, 1022
ESCALA = 2          # se dibuja al doble de tamaño y luego se reduce: bordes más suaves
VIOLETA = (139, 92, 246)     # los mismos colores de la app (tunedrop/ui/theme.py)
FUCSIA = (217, 70, 239)
OSCURO = (46, 16, 101)


def mezclar(a: tuple, b: tuple, t: float) -> tuple:
    """Color intermedio entre a y b (t = 0 es a, t = 1 es b)."""
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def degradado(ancho: int, alto: int) -> Image.Image:
    """Degradado en diagonal: violeta arriba a la izquierda, fucsia abajo a la derecha."""
    # Se calcula pequeño y se amplía: da el mismo resultado y es mucho más rápido.
    pequeno = Image.new("RGB", (64, 128))
    for y in range(128):
        for x in range(64):
            t = (x / 63 * 0.35) + (y / 127 * 0.65)
            pequeno.putpixel((x, y), mezclar(VIOLETA, FUCSIA, t))
    return pequeno.resize((ancho, alto), Image.BICUBIC).convert("RGBA")


def nota_blanca(alto: int) -> Image.Image:
    """La nota musical ♫ en blanco, dibujada con la letra Segoe UI Symbol de Windows.

    Es una letra (vectorial), así que sale nítida a cualquier tamaño.
    """
    letra = fuente("seguisym.ttf", alto)
    caja = letra.getbbox("♫")                   # el espacio que ocupa el símbolo
    nota = Image.new("RGBA", (caja[2] - caja[0], caja[3] - caja[1]), (255, 255, 255, 0))
    ImageDraw.Draw(nota).text((-caja[0], -caja[1]), "♫", font=letra, fill="white")
    return nota


def fuente(nombre: str, tamano: int) -> ImageFont.ImageFont:
    """Segoe UI (la letra de Windows). Si no está, la letra básica de Pillow."""
    try:
        return ImageFont.truetype(nombre, tamano)
    except OSError:
        return ImageFont.load_default(tamano)


def imagen_lateral() -> Image.Image:
    w, h = ANCHO * ESCALA, ALTO * ESCALA
    lienzo = degradado(w, h)

    # Círculos grandes y casi transparentes de adorno (como luces desenfocadas).
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    for cx, cy, r, alfa in [(-0.15, 0.08, 0.55, 28), (1.1, 0.42, 0.45, 22), (0.2, 0.98, 0.5, 26)]:
        d.ellipse([(cx - r) * w, cy * h - r * w, (cx + r) * w, cy * h + r * w], fill=(255, 255, 255, alfa))
    lienzo = Image.alpha_composite(lienzo, capa.filter(ImageFilter.GaussianBlur(8 * ESCALA)))

    # Sombra suave y nota musical blanca.
    nota = nota_blanca(round(w * 0.5))
    x, y = (w - nota.width) // 2, round(h * 0.2)
    sombra = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sombra.paste((*OSCURO, 110), (x, y + 10 * ESCALA), nota)
    lienzo = Image.alpha_composite(lienzo, sombra.filter(ImageFilter.GaussianBlur(14 * ESCALA)))
    lienzo.alpha_composite(nota, (x, y))

    # Nombre y lema.
    d = ImageDraw.Draw(lienzo)
    d.text((w / 2, h * 0.53), "tunedrop", font=fuente("segoeuib.ttf", 70 * ESCALA),
           fill="white", anchor="mm")
    d.text((w / 2, h * 0.595), "Tu música, lista para tu iPod", font=fuente("segoeui.ttf", 27 * ESCALA),
           fill=(255, 255, 255, 215), anchor="mm")

    # Barras de ecualizador abajo, cada una de una altura (siempre las mismas: semilla fija).
    capa = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(capa)
    azar = random.Random(7)
    barras, hueco = 13, 12 * ESCALA
    ancho_barra = (w - 2 * 48 * ESCALA - (barras - 1) * hueco) / barras
    base = h * 0.9
    for i in range(barras):
        # Más altas en el centro, como una onda de sonido.
        centro = 1 - abs(i - (barras - 1) / 2) / ((barras - 1) / 2)
        alto = (0.05 + 0.13 * centro + azar.uniform(0, 0.06)) * h
        x0 = 48 * ESCALA + i * (ancho_barra + hueco)
        d.rounded_rectangle([x0, base - alto, x0 + ancho_barra, base], radius=ancho_barra / 2,
                            fill=(255, 255, 255, 70 + round(60 * centro)))
    lienzo = Image.alpha_composite(lienzo, capa)

    return lienzo.resize((ANCHO, ALTO), Image.LANCZOS).convert("RGB")


def imagen_icono() -> Image.Image:
    return Image.open(ICONO).convert("RGBA").resize((159, 159), Image.LANCZOS)


if __name__ == "__main__":
    imagen_lateral().save(PACKAGING / "instalador-lateral.png", optimize=True)
    imagen_icono().save(PACKAGING / "instalador-icono.png", optimize=True)
    print("Creadas packaging/instalador-lateral.png y packaging/instalador-icono.png")
