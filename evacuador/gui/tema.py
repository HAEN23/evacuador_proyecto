"""Paleta, tipografía y estilos compartidos por todas las vistas de la interfaz.

Es el único módulo que define la apariencia. ``app``, ``editor`` y ``resultado``
dependen de él, y ninguno depende de los otros dos.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk
from typing import Final

from ..config import (BLOQUEADA, COLOR_ALERTA, COLOR_BLOQUEADA, COLOR_INICIO,
                      COLOR_RUTA, COSTO_MAX, COSTO_MIN)

COLORES: Final[dict[str, str]] = {
    "fondo": "#F3F5F8",
    "superficie": "#FFFFFF",
    "borde": "#D9DFE7",
    "primario": COLOR_RUTA,
    "primario_hover": "#0F2540",
    "primario_presionado": "#0A1B30",
    "acento": "#C8102E",
    "texto": "#1E2A38",
    "texto_secundario": "#5B6B7D",
    "texto_tenue": "#8593A3",
    "texto_invertido": "#FFFFFF",
    "texto_invertido_suave": "#B8C7D9",
    "secundario": "#EEF2F6",
    "secundario_hover": "#E1E7EE",
    "exito": COLOR_INICIO,
    "error": COLOR_ALERTA,
    "celda_bloqueada": COLOR_BLOQUEADA,
    "celda_libre": "#FFFFFF",
    "celda_libre_marcada": "#CDEBD8",
    "riesgo_bajo": "#F6D365",
    "riesgo_alto": COLOR_ALERTA,
}

FUENTES_PREFERIDAS: Final[tuple[str, ...]] = (
    "Segoe UI", "SF Pro Text", "Helvetica Neue", "Inter",
    "Roboto", "Ubuntu", "DejaVu Sans", "Arial",
)

ANCHO_TEXTO: Final[int] = 440
"""Ancho máximo (en píxeles) de los párrafos dentro de los paneles."""


def elegir_fuente() -> str:
    """Devuelve la primera familia tipográfica disponible en el sistema."""
    disponibles = set(tkfont.families())
    for familia in FUENTES_PREFERIDAS:
        if familia in disponibles:
            return familia
    return "TkDefaultFont"


def hex_a_rgb(color: str) -> tuple[int, int, int]:
    """Convierte un color ``#RRGGBB`` en una tupla ``(r, g, b)``."""
    return int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)


def degradado_riesgo(t: float) -> str:
    """Color entre riesgo bajo (``t = 0``) y riesgo alto (``t = 1``)."""
    inicio, fin = hex_a_rgb(COLORES["riesgo_bajo"]), hex_a_rgb(COLORES["riesgo_alto"])
    r, g, b = (round(a + (z - a) * t) for a, z in zip(inicio, fin))
    return f"#{r:02x}{g:02x}{b:02x}"


def color_celda(valor: int) -> str:
    """Color de relleno de una celda según su valor (0 bloqueada, 1 libre, 2-99 humo)."""
    if valor == BLOQUEADA:
        return COLORES["celda_bloqueada"]
    if valor == COSTO_MIN:
        return COLORES["celda_libre"]
    return degradado_riesgo((valor - 2) / max(COSTO_MAX - 2, 1))


def muestra_color(padre: tk.Misc, color: str, ancho: int = 28, alto: int = 18) -> tk.Canvas:
    """Recuadro de color sólido para la leyenda."""
    lienzo = tk.Canvas(padre, width=ancho, height=alto, bg=COLORES["superficie"],
                       highlightthickness=0, bd=0)
    lienzo.create_rectangle(1, 1, ancho - 1, alto - 1, fill=color, outline=COLORES["borde"])
    return lienzo


def muestra_degradado(padre: tk.Misc, ancho: int = 28, alto: int = 18) -> tk.Canvas:
    """Recuadro con degradado de riesgo bajo a riesgo alto."""
    lienzo = tk.Canvas(padre, width=ancho, height=alto, bg=COLORES["superficie"],
                       highlightthickness=0, bd=0)
    for x in range(1, ancho - 1):
        lienzo.create_line(x, 1, x, alto - 1,
                           fill=degradado_riesgo((x - 1) / max(ancho - 3, 1)))
    lienzo.create_rectangle(1, 1, ancho - 1, alto - 1, outline=COLORES["borde"])
    return lienzo


def configurar_estilos(raiz: tk.Misc, f: str) -> None:
    """Registra los estilos ``ttk`` de la aplicación.

    Args:
        raiz: Ventana raíz.
        f: Familia tipográfica (ver :func:`elegir_fuente`).
    """
    c = COLORES
    estilo = ttk.Style(raiz)
    if "clam" in estilo.theme_names():
        estilo.theme_use("clam")

    estilo.configure("App.TFrame", background=c["fondo"])
    estilo.configure("Header.TFrame", background=c["primario"])
    estilo.configure("Card.TFrame", background=c["superficie"])
    estilo.configure("Status.TFrame", background=c["superficie"])

    estilo.configure("Eyebrow.TLabel", background=c["primario"],
                     foreground=c["texto_invertido_suave"], font=(f, 9, "bold"))
    estilo.configure("HeaderTitle.TLabel", background=c["primario"],
                     foreground=c["texto_invertido"], font=(f, 22, "bold"))
    estilo.configure("HeaderSubtitle.TLabel", background=c["primario"],
                     foreground=c["texto_invertido_suave"], font=(f, 11))
    estilo.configure("Version.TLabel", background=c["primario"],
                     foreground=c["texto_invertido_suave"], font=(f, 9))

    estilo.configure("CardEyebrow.TLabel", background=c["superficie"],
                     foreground=c["acento"], font=(f, 9, "bold"))
    estilo.configure("SectionTitle.TLabel", background=c["superficie"],
                     foreground=c["primario"], font=(f, 16, "bold"))
    estilo.configure("Subsection.TLabel", background=c["superficie"],
                     foreground=c["primario"], font=(f, 10, "bold"))
    estilo.configure("Body.TLabel", background=c["superficie"],
                     foreground=c["texto_secundario"], font=(f, 10))
    estilo.configure("Term.TLabel", background=c["superficie"],
                     foreground=c["texto"], font=(f, 10, "bold"))
    estilo.configure("Hint.TLabel", background=c["superficie"],
                     foreground=c["texto_tenue"], font=(f, 9))
    estilo.configure("Status.TLabel", background=c["superficie"],
                     foreground=c["texto_secundario"], font=(f, 9))

    for nombre, color in (("Exito", c["exito"]), ("Error", c["error"])):
        estilo.configure(f"{nombre}.Result.TLabel", background=c["superficie"],
                         foreground=color, font=(f, 11, "bold"))

    estilo.configure("Tool.TRadiobutton", background=c["superficie"],
                     foreground=c["texto"], font=(f, 10))
    estilo.map("Tool.TRadiobutton", background=[("active", c["superficie"])])

    estilo.configure("Primary.TButton", font=(f, 11, "bold"), padding=(20, 12),
                     background=c["primario"], foreground=c["texto_invertido"],
                     borderwidth=0, focusthickness=0, relief="flat")
    estilo.map("Primary.TButton",
               background=[("pressed", c["primario_presionado"]),
                           ("active", c["primario_hover"])],
               foreground=[("disabled", c["texto_invertido_suave"])])

    estilo.configure("Secondary.TButton", font=(f, 11), padding=(20, 11),
                     background=c["secundario"], foreground=c["primario"],
                     bordercolor=c["borde"], borderwidth=1, focusthickness=0,
                     relief="flat")
    estilo.map("Secondary.TButton",
               background=[("pressed", c["borde"]),
                           ("active", c["secundario_hover"])])

    for orientacion in ("Vertical", "Horizontal"):
        estilo.configure(
            f"Panel.{orientacion}.TScrollbar", troughcolor=c["fondo"],
            background=c["secundario_hover"], bordercolor=c["borde"],
            lightcolor=c["secundario_hover"], darkcolor=c["secundario_hover"],
            arrowcolor=c["texto_secundario"], gripcount=0)
