"""Visualización en terminal (ASCII, animada) y gráfica (matplotlib, opcional)."""
from __future__ import annotations

import time
from typing import Iterable

from .config import (BLOQUEADA, COLOR_ALERTA, COLOR_BLOQUEADA, COLOR_EXPLORADA,
                     COLOR_INICIO, COLOR_RUTA, COLOR_SALIDA, COSTO_MAX, COSTO_MIN,
                     UMBRAL_HUMO)
from .modelos import Escenario, Posicion, Resultado

LEYENDA = ("# bloqueada | . limpia | + humo leve | % humo denso | "
           "o explorada | * ruta final | S inicio | G salida")


def _simbolo(esc: Escenario, pos: Posicion, ruta: set[Posicion], vistos: set[Posicion]) -> str:
    if pos == esc.inicio:
        return "S"
    if pos in esc.metas:
        return "G"
    if pos in ruta:
        return "*"
    if pos in vistos:
        return "o"
    valor = esc.costo(pos)
    if valor == BLOQUEADA:
        return "#"
    if valor < UMBRAL_HUMO:
        return "."
    return "+" if valor < 50 else "%"


def render_ascii(esc: Escenario, ruta: Iterable[Posicion] | None = None,
                 explorados: Iterable[Posicion] | None = None) -> str:
    r, v = set(ruta or ()), set(explorados or ())
    return "\n".join(
        " ".join(_simbolo(esc, (i, j), r, v) for j in range(esc.columnas))
        for i in range(esc.filas)
    )


def mostrar_resultado(esc: Escenario, res: Resultado) -> None:
    print(render_ascii(esc, res.ruta, res.explorados))
    print(f"\n{LEYENDA}\n")
    if not res.encontrada:
        print("SIN RUTA: no existe camino seguro hacia ninguna salida.")
        print(f"Nodos expandidos: {res.nodos_expandidos}")
        return
    print(f"Costo de riesgo acumulado : {res.costo}")
    print(f"Longitud (pasos)          : {res.pasos}")
    print(f"Celdas de humo atravesadas: {res.celdas_humo}")
    print(f"Nodos expandidos          : {res.nodos_expandidos}")
    print(f"Tiempo de ejecución       : {res.tiempo_ms:.2f} ms")


def animar(esc: Escenario, res: Resultado, pausa: float = 0.05) -> None:
    """Dibuja la expansión de UCS nodo por nodo."""
    total = len(res.explorados)
    for i in range(1, total + 1):
        print("\033[H\033[J", end="")
        print(f"Expandiendo nodo {i}/{total} -> {res.explorados[i - 1]}")
        print(render_ascii(esc, explorados=res.explorados[:i]))
        time.sleep(pausa)
    print("\033[H\033[J", end="")


def dibujar_mapa(figura, ejes, esc: Escenario, res: Resultado) -> None:
    """Dibuja el mapa de riesgo, el área explorada y la ruta sobre unos ejes de matplotlib.

    Es el único lugar donde se dibuja el mapa: lo usan tanto ``graficar`` (ventana
    independiente) como la vista de resultados de la interfaz gráfica.

    Args:
        figura: ``Figure`` que contiene los ejes (debe usar diseño "constrained").
        ejes: ``Axes`` donde se dibuja.
        esc: Escenario resuelto.
        res: Resultado de la búsqueda.
    """
    import matplotlib.patches as mpatches
    import numpy as np
    from matplotlib import colormaps
    from matplotlib.ticker import MaxNLocator

    datos = np.array(esc.grid, dtype=float)
    datos[datos == BLOQUEADA] = np.nan
    mapa = colormaps["YlOrRd"].with_extremes(bad=COLOR_BLOQUEADA)
    imagen = ejes.imshow(datos, cmap=mapa, vmin=COSTO_MIN, vmax=COSTO_MAX)
    figura.colorbar(imagen, ax=ejes, label="Concentración de tóxico (costo)", shrink=0.9)

    if res.explorados:
        ejes.scatter([c for _, c in res.explorados], [r for r, _ in res.explorados],
                     c=COLOR_EXPLORADA, s=14, alpha=0.6, label="Área explorada (UCS)")
    if res.ruta:
        columnas, filas = [c for _, c in res.ruta], [r for r, _ in res.ruta]
        ejes.plot(columnas, filas, "-", color="white", lw=5, zorder=2)
        ejes.plot(columnas, filas, "-", color=COLOR_RUTA, lw=2.5, zorder=3,
                  label="Ruta óptima de escape")
    ejes.scatter(esc.inicio[1], esc.inicio[0], c=COLOR_INICIO, edgecolors="white",
                 s=140, zorder=4, label="Punto de inicio")
    for i, (r, c) in enumerate(esc.metas):
        ejes.scatter(c, r, c=COLOR_SALIDA, edgecolors="white", marker="*", s=300, zorder=4,
                     label="Salida de emergencia" if i == 0 else None)

    manejadores, _ = ejes.get_legend_handles_labels()
    manejadores.append(mpatches.Patch(color=COLOR_BLOQUEADA, label="Bloqueada (fuego / pared)"))
    figura.legend(handles=manejadores, loc="outside lower center", ncol=3, fontsize=9,
                  frameon=False)

    ejes.set_title("Ruta de evacuación de menor riesgo acumulado" if res.encontrada
                   else "Situación crítica: el agente no puede alcanzar ninguna salida",
                   color=COLOR_RUTA if res.encontrada else COLOR_ALERTA,
                   fontsize=12, fontweight="bold")
    ejes.set_xlabel("Columna")
    ejes.set_ylabel("Fila")
    ejes.xaxis.set_major_locator(MaxNLocator(integer=True))
    ejes.yaxis.set_major_locator(MaxNLocator(integer=True))


def nueva_figura(facecolor: str = "white"):
    """Crea una ``Figure`` con diseño "constrained" (compatible con matplotlib 3.7 o superior)."""
    from matplotlib.figure import Figure
    return Figure(figsize=(9, 6.5), dpi=100, facecolor=facecolor, layout="constrained")


def graficar(esc: Escenario, res: Resultado) -> None:
    """Muestra el mapa en una ventana de matplotlib."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Para el gráfico instale: pip install matplotlib numpy")
        return
    figura = plt.figure(figsize=(11, 7), layout="constrained")
    dibujar_mapa(figura, figura.add_subplot(111), esc, res)
    plt.show()
