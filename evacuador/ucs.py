"""Búsqueda de Costo Uniforme (UCS). Sin heurística: solo el costo real g(n)."""
from __future__ import annotations

import heapq
import time

from .config import UMBRAL_HUMO
from .modelos import Escenario, Posicion, Resultado

# g(n) suma los costos de las celdas a las que se entra; el inicio cuesta 0.

def buscar_ucs(escenario: Escenario) -> Resultado:
    """Devuelve la ruta de menor riesgo acumulado hacia la salida más barata.

    La prueba de meta se hace al EXPANDIR el nodo (no al generarlo), lo que
    garantiza optimalidad. Si no existe ruta, la frontera se agota y se
    devuelve un Resultado sin ruta (nunca hay bucle infinito).
    """
    t0 = time.perf_counter()
    # El conjunto permite consultar en O(1) si una posición es meta.
    metas = set(escenario.metas)
    inicio = escenario.inicio

    # Un inicio bloqueado no permite comenzar la búsqueda.
    if not escenario.es_transitable(inicio):
        return _sin_ruta(0, [], t0)

    # La frontera es un min-heap de (costo acumulado, posición); al empatar,
    # heapq desempata por posición y mantiene el resultado determinista.
    frontera: list[tuple[int, Posicion]] = [(0, inicio)]
    # Mejor costo conocido para alcanzar cada posición.
    mejor_g: dict[Posicion, int] = {inicio: 0}
    # Permite reconstruir la ruta; el inicio no tiene padre.
    padre: dict[Posicion, Posicion | None] = {inicio: None}
    # Cada posición cerrada ya fue expandida con su costo mínimo.
    cerrados: set[Posicion] = set()
    # Orden de expansión usado como rastro de búsqueda y para la animación.
    orden: list[Posicion] = []

    while frontera:
        g, estado = heapq.heappop(frontera)
        if estado in cerrados:
            # heapq no actualiza prioridades: las entradas antiguas se ignoran
            # cuando salen después de haber encontrado un camino más barato.
            continue  # entrada obsoleta de la cola de prioridad
        cerrados.add(estado)
        orden.append(estado)

        # La meta se comprueba al expandir: con costos positivos, su costo ya
        # es mínimo al salir del heap. Comprobarla al generar podría aceptar
        # una ruta más cara antes de descubrir otra más barata.
        if estado in metas:
            ruta = _reconstruir(padre, estado)
            # Cuenta las celdas de la ruta cuyo costo alcanza el umbral de humo.
            humo = sum(1 for p in ruta if escenario.costo(p) >= UMBRAL_HUMO)
            return Resultado(tuple(ruta), g, len(orden), tuple(orden),
                             _ms(t0), humo)

        # Solo se generan vecinos dentro del mapa y que no estén bloqueados.
        for vecino in escenario.vecinos_transitables(estado):
            # El costo de un movimiento incluye el costo de entrar al vecino.
            nuevo_g = g + escenario.costo(vecino)
            # Conserva solo caminos que mejoren el costo conocido para el vecino.
            if nuevo_g < mejor_g.get(vecino, float("inf")):
                mejor_g[vecino] = nuevo_g
                padre[vecino] = estado
                heapq.heappush(frontera, (nuevo_g, vecino))

    # La frontera vacía indica que no hay ruta; cada posición se expande una vez.
    return _sin_ruta(len(orden), orden, t0)


# Sigue los padres desde la meta hasta el inicio y devuelve la ruta en orden.
def _reconstruir(padre: dict[Posicion, Posicion | None], meta: Posicion) -> list[Posicion]:
    ruta: list[Posicion] = []
    actual: Posicion | None = meta
    while actual is not None:
        ruta.append(actual)
        actual = padre[actual]
    # Invierte la ruta para dejarla en orden inicio → meta.
    return ruta[::-1]


# Convierte a milisegundos el tiempo transcurrido desde t0.
def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000


# Crea un resultado sin ruta y conserva las métricas de búsqueda.
def _sin_ruta(expandidos: int, orden: list[Posicion], t0: float) -> Resultado:
    return Resultado(None, None, expandidos, tuple(orden), _ms(t0))
