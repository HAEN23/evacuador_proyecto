"""Gráficas del AG: evolución de la aptitud, top 3 sobre el mapa y curva de evacuación.

Igual que visualizacion.py: las funciones de dibujo reciben figura y ejes (para poder
reutilizarlas en la GUI) y matplotlib se importa dentro de las funciones, así el núcleo y
el CLI no lo exigen. No imprime: las tablas de texto y CSV están en experimentos_ag.py.
"""
from __future__ import annotations

from pathlib import Path

from .config import (BLOQUEADA, COLOR_ALERTA, COLOR_BLOQUEADA, COLOR_INICIO, COLOR_RUTA,
                     COLOR_SALIDA, COSTO_MAX, COSTO_MIN)
from .genetico import Configuracion, Grupo, ResultadoAG
from .modelos import Escenario, Posicion
from .ucs import buscar_ucs

# Un color por puesto del top 3 en la curva de evacuación.
COLORES_TOP3 = (COLOR_RUTA, "#E65100", "#6A1B9A")


def _como_grupo(dato) -> Grupo:
    """Acepta Grupo, (fila, col) o (fila, col, tamaño), igual que `optimizar`."""
    if isinstance(dato, Grupo):
        return dato
    return Grupo((dato[0], dato[1]), dato[2] if len(dato) == 3 else 1)


def rutas_grupos(escenario: Escenario, grupos,
                 salidas: tuple[Posicion, ...]) -> list[list[Posicion] | None]:
    """Ruta de menor riesgo de cada grupo hacia la salida que le conviene (None si no llega)."""
    if not salidas:
        return [None for _ in grupos]
    rutas: list[list[Posicion] | None] = []
    for grupo in map(_como_grupo, grupos):
        res = buscar_ucs(Escenario(escenario.grid, grupo.celda, salidas))
        rutas.append(list(res.ruta) if res.encontrada else None)
    return rutas


def dibujar_evolucion(figura, ejes, resultado: ResultadoAG) -> None:
    """Aptitud del mejor, del promedio y del peor individuo por generación."""
    from matplotlib.ticker import MaxNLocator

    gens = [g.numero for g in resultado.historial]
    ejes.plot(gens, [g.aptitud_mejor for g in resultado.historial], color=COLOR_RUTA,
              lw=2.2, label="Mejor")
    ejes.plot(gens, [g.aptitud_promedio for g in resultado.historial], color=COLOR_SALIDA,
              lw=1.6, ls="--", label="Promedio")
    ejes.plot(gens, [g.aptitud_peor for g in resultado.historial], color=COLOR_ALERTA,
              lw=1.2, ls=":", label="Peor")
    ejes.set_title("Evolución de la aptitud", fontsize=12, fontweight="bold")
    ejes.set_xlabel("Generación")
    ejes.set_ylabel("Aptitud")
    ejes.set_ylim(bottom=0)
    ejes.xaxis.set_major_locator(MaxNLocator(integer=True))
    ejes.grid(alpha=0.3)
    ejes.legend(frameon=False)


def dibujar_configuracion(figura, ejes, escenario: Escenario, grupos, conf: Configuracion,
                          titulo: str = "", barra: bool = True) -> None:
    """Mapa de riesgo con las salidas de `conf` y la ruta de cada grupo.

    Mismo estilo que `visualizacion.dibujar_mapa`: muros oscuros y humo en escala YlOrRd.
    """
    import numpy as np
    from matplotlib import colormaps
    from matplotlib.ticker import MaxNLocator

    datos = np.array(escenario.grid, dtype=float)
    datos[datos == BLOQUEADA] = np.nan
    mapa = colormaps["YlOrRd"].with_extremes(bad=COLOR_BLOQUEADA)
    imagen = ejes.imshow(datos, cmap=mapa, vmin=COSTO_MIN, vmax=COSTO_MAX)
    if barra:
        figura.colorbar(imagen, ax=ejes, label="Concentración de tóxico (costo)", shrink=0.9)

    grupos = [_como_grupo(g) for g in grupos]
    rutas = rutas_grupos(escenario, grupos, conf.salidas)
    for i, ruta in enumerate(r for r in rutas if r):
        columnas, filas = [c for _, c in ruta], [f for f, _ in ruta]
        ejes.plot(columnas, filas, "-", color="white", lw=4, zorder=2)
        ejes.plot(columnas, filas, "-", color=COLOR_RUTA, lw=2, zorder=3,
                  label="Ruta de un grupo" if i == 0 else None)
    # El tamaño del círculo crece con el número de personas del grupo.
    con_ruta = [g for g, r in zip(grupos, rutas) if r]
    sin_ruta = [g for g, r in zip(grupos, rutas) if not r]
    if con_ruta:
        ejes.scatter([g.celda[1] for g in con_ruta], [g.celda[0] for g in con_ruta],
                     s=[40 + 15 * g.tamano for g in con_ruta], c=COLOR_INICIO,
                     edgecolors="white", zorder=4, label="Grupo (tamaño = personas)")
    if sin_ruta:
        ejes.scatter([g.celda[1] for g in sin_ruta], [g.celda[0] for g in sin_ruta],
                     s=80, c=COLOR_ALERTA, marker="X", edgecolors="white", zorder=4,
                     label="Grupo sin ruta")
    if conf.salidas:
        ejes.scatter([c for _, c in conf.salidas], [f for f, _ in conf.salidas],
                     c=COLOR_SALIDA, edgecolors="white", marker="*", s=320, zorder=5,
                     label="Salida de emergencia")
    ejes.set_title(titulo or f"Aptitud {conf.aptitud:.4f}", fontsize=11, fontweight="bold")
    ejes.set_xlabel("Columna")
    ejes.set_ylabel("Fila")
    ejes.xaxis.set_major_locator(MaxNLocator(integer=True))
    ejes.yaxis.set_major_locator(MaxNLocator(integer=True))


def dibujar_top3(figura, escenario: Escenario, grupos, resultado: ResultadoAG) -> None:
    """Las (hasta) tres mejores configuraciones lado a lado sobre `figura`."""
    import matplotlib.patches as mpatches

    n = len(resultado.top3)
    lista_ejes = figura.subplots(1, n, squeeze=False)[0]
    for i, (ejes, conf) in enumerate(zip(lista_ejes, resultado.top3), start=1):
        dibujar_configuracion(figura, ejes, escenario, grupos, conf,
                              titulo=f"#{i}  aptitud {conf.aptitud:.4f}", barra=i == n)
    manejadores, _ = lista_ejes[0].get_legend_handles_labels()
    manejadores.append(mpatches.Patch(color=COLOR_BLOQUEADA, label="Muro"))
    figura.legend(handles=manejadores, loc="outside lower center", ncol=len(manejadores),
                  fontsize=9, frameon=False)


def dibujar_mapa_detallado(figura, escenario: Escenario, grupos, conf: Configuracion,
                           puesto: int) -> None:
    """Una sola configuración a tamaño completo: numeración de cada celda, cuadrícula y
    las personas que llegan a cada salida."""
    import matplotlib.patches as mpatches

    ejes = figura.add_subplot(111)
    dibujar_configuracion(figura, ejes, escenario, grupos, conf,
                          titulo=f"#{puesto}  ·  aptitud {conf.aptitud:.4f}  ·  "
                                 f"salen {100 * conf.o1:.0f} %  ·  T90 {conf.t90} s")
    filas, columnas = len(escenario.grid), len(escenario.grid[0])
    ejes.set_xticks(range(columnas))
    ejes.set_yticks(range(filas))
    ejes.tick_params(labelsize=8)
    ejes.set_xticks([c - 0.5 for c in range(1, columnas)], minor=True)
    ejes.set_yticks([f - 0.5 for f in range(1, filas)], minor=True)
    ejes.grid(which="minor", color="white", lw=0.5, alpha=0.6)
    ejes.tick_params(which="minor", length=0)
    for (f, c), n in zip(conf.salidas, conf.personas_por_salida):
        ejes.annotate(f"({f},{c})  {n} pers.", (c, f),
                      xytext=(0, -16 if f == 0 else 14),  # en la fila 0 taparía el título
                      textcoords="offset points", ha="center", va="center", fontsize=9,
                      fontweight="bold", color=COLOR_SALIDA, zorder=6,
                      bbox=dict(boxstyle="round,pad=0.2", fc="white", ec=COLOR_SALIDA, lw=0.8))
    manejadores, _ = ejes.get_legend_handles_labels()
    manejadores.append(mpatches.Patch(color=COLOR_BLOQUEADA, label="Muro"))
    figura.legend(handles=manejadores, loc="outside lower center", ncol=2,
                  fontsize=9, frameon=False)


def dibujar_curvas(figura, ejes, resultado: ResultadoAG) -> None:
    """Porcentaje acumulado de personas evacuadas contra segundos, una curva por puesto."""
    for i, conf in enumerate(resultado.top3, start=1):
        color = COLORES_TOP3[(i - 1) % len(COLORES_TOP3)]
        if not conf.curva_evacuacion:  # nadie llega a una salida: no hay curva
            ejes.plot([], [], color=color, label=f"#{i} (nadie sale)")
            continue
        # Escalón desde (0, 0): el porcentaje sube cuando llega cada grupo.
        tiempos = [0] + [t for t, _ in conf.curva_evacuacion]
        porcentajes = [0.0] + [100 * p for _, p in conf.curva_evacuacion]
        ejes.step(tiempos, porcentajes, where="post", color=color, lw=2,
                  label=f"#{i}  {_texto_salidas(conf)}")
    ejes.set_title("Personas evacuadas contra tiempo", fontsize=12, fontweight="bold")
    ejes.set_xlabel("Tiempo (s)")
    ejes.set_ylabel("Personas evacuadas (%)")
    ejes.set_ylim(0, 105)
    ejes.grid(alpha=0.3)
    ejes.legend(frameon=False, fontsize=9)


def _texto_salidas(conf: Configuracion) -> str:
    return " ".join(f"({f},{c})" for f, c in conf.salidas)


def guardar_figuras(carpeta: str | Path, escenario: Escenario, grupos,
                    resultado: ResultadoAG) -> list[Path]:
    """Guarda las tres figuras como PNG en `carpeta` y devuelve sus rutas.

    Lanza RuntimeError si matplotlib no está instalado.
    """
    try:
        from matplotlib.figure import Figure
    except ImportError as exc:
        raise RuntimeError("Para las figuras instale: pip install -r requirements.txt") from exc
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    rutas = []

    figura = Figure(figsize=(8, 5), dpi=120, layout="constrained")
    dibujar_evolucion(figura, figura.add_subplot(111), resultado)
    rutas.append(_guardar(figura, carpeta / "evolucion_aptitud.png"))

    figura = Figure(figsize=(6 * len(resultado.top3), 5.5), dpi=120, layout="constrained")
    dibujar_top3(figura, escenario, grupos, resultado)
    rutas.append(_guardar(figura, carpeta / "top3_mapa.png"))

    figura = Figure(figsize=(8, 5), dpi=120, layout="constrained")
    dibujar_curvas(figura, figura.add_subplot(111), resultado)
    rutas.append(_guardar(figura, carpeta / "curva_evacuacion.png"))
    return rutas


def _guardar(figura, ruta: Path) -> Path:
    figura.savefig(ruta)
    return ruta
