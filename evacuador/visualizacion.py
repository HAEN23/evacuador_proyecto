"""Visualización en terminal (ASCII, animada) y gráfica (matplotlib, opcional)."""
from __future__ import annotations

import time
from typing import Iterable

from .config import BLOQUEADA, UMBRAL_HUMO
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


def graficar(esc: Escenario, res: Resultado) -> None:
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        import matplotlib.patches as mpatches
    except ImportError:
        print("Para el gráfico instale: pip install matplotlib numpy")
        return

    plt.figure(figsize=(12, 7))
    datos = np.array(esc.grid, dtype=float)
    datos[datos == BLOQUEADA] = np.nan
    cmap = plt.cm.YlOrRd.copy()
    cmap.set_bad("black")
    plt.imshow(datos, cmap=cmap, vmin=1, vmax=99)
    plt.colorbar(label="Nivel de Riesgo (Concentración de tóxico)", shrink=0.85)

    plt.grid(which="major", color="black", linestyle="-", linewidth=0.5, alpha=0.3)
    plt.xticks(np.arange(-0.5, esc.columnas, 1), [])
    plt.yticks(np.arange(-0.5, esc.filas, 1), [])

    if res.explorados:
        plt.scatter([c for _, c in res.explorados], [r for r, _ in res.explorados],
                    c="cyan", s=25, alpha=0.6, label="Área Explorada (UCS)")
    if res.ruta:
        plt.plot([c for _, c in res.ruta], [r for r, _ in res.ruta],
                 "w-", lw=5, zorder=2)
        plt.plot([c for _, c in res.ruta], [r for r, _ in res.ruta],
                 "b-", lw=2.5, label="Ruta Óptima de Escape", zorder=3)

    plt.scatter(esc.inicio[1], esc.inicio[0], c="lime", edgecolors="black",
                s=150, label="Punto de Inicio", zorder=4)
    for r, c in esc.metas:
        plt.scatter(c, r, c="fuchsia", edgecolors="black", marker="*", s=300,
                    label="Salida de Emergencia", zorder=4)

    parche_bloqueo = mpatches.Patch(color="black", label="Celdas Bloqueadas (Fuego / Pared)")
    handles, _ = plt.gca().get_legend_handles_labels()
    handles.append(parche_bloqueo)
    plt.legend(handles=handles, loc="upper right", framealpha=0.9, edgecolor="black", fontsize=10)
    plt.title("Sistema de Evacuación Táctica - Ruta de Menor Riesgo Acumulado",
              fontsize=15, fontweight="bold")
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    plt.show()
