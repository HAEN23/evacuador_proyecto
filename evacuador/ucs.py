"""Búsqueda de Costo Uniforme (UCS). Sin heurística: solo el costo real g(n)."""
from __future__ import annotations

import heapq
import time

from .config import UMBRAL_HUMO
from .modelos import Escenario, Posicion, Resultado


def buscar_ucs(escenario: Escenario) -> Resultado:
    """Devuelve la ruta de menor riesgo acumulado hacia la salida más barata.

    La prueba de meta se hace al EXPANDIR el nodo (no al generarlo), lo que
    garantiza optimalidad. Si no existe ruta, la frontera se agota y se
    devuelve un Resultado sin ruta (nunca hay bucle infinito).
    """
    t0 = time.perf_counter()
    metas = set(escenario.metas)
    inicio = escenario.inicio

    if not escenario.es_transitable(inicio):
        return _sin_ruta(0, [], t0)

    frontera: list[tuple[int, Posicion]] = [(0, inicio)]
    mejor_g: dict[Posicion, int] = {inicio: 0}
    padre: dict[Posicion, Posicion | None] = {inicio: None}
    cerrados: set[Posicion] = set()
    orden: list[Posicion] = []

    while frontera:
        g, estado = heapq.heappop(frontera)
        if estado in cerrados:
            continue  # entrada obsoleta de la cola de prioridad
        cerrados.add(estado)
        orden.append(estado)

        if estado in metas:
            ruta = _reconstruir(padre, estado)
            humo = sum(1 for p in ruta if escenario.costo(p) >= UMBRAL_HUMO)
            return Resultado(tuple(ruta), g, len(orden), tuple(orden),
                             _ms(t0), humo)

        for vecino in escenario.vecinos_transitables(estado):
            nuevo_g = g + escenario.costo(vecino)
            if nuevo_g < mejor_g.get(vecino, float("inf")):
                mejor_g[vecino] = nuevo_g
                padre[vecino] = estado
                heapq.heappush(frontera, (nuevo_g, vecino))

    return _sin_ruta(len(orden), orden, t0)


def _reconstruir(padre: dict[Posicion, Posicion | None], meta: Posicion) -> list[Posicion]:
    ruta: list[Posicion] = []
    actual: Posicion | None = meta
    while actual is not None:
        ruta.append(actual)
        actual = padre[actual]
    return ruta[::-1]


def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000


def _sin_ruta(expandidos: int, orden: list[Posicion], t0: float) -> Resultado:
    return Resultado(None, None, expandidos, tuple(orden), _ms(t0))
