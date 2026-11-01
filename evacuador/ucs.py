"""Búsqueda de Costo Uniforme (UCS). Sin heurística: solo el costo real g(n).

=== GUÍA PARA LA DEFENSA (léase antes de exponer) ===================================

Idea en una frase:
    UCS siempre expande primero el estado cuyo costo acumulado g(n) es el MENOR de
    todos los pendientes. Por eso, cuando por fin sale la salida, ya no puede
    existir un camino más barato: es la ruta óptima.

Analogía fácil:
    Es como una libreta con "caminos pendientes", cada uno con el riesgo que lleva
    sumado. Siempre se continúa el camino con menos riesgo acumulado. Esa libreta
    es la FRONTERA (``frontera``), implementada con un heap (cola de prioridad).

Qué costo se suma:
    El costo de un paso es el valor de la celda A LA QUE SE ENTRA (no de la que se
    sale). El inicio cuesta 0. Una celda limpia vale 1, el humo vale 2..99 y el 0
    es pared/fuego (intransitable, ni siquiera se genera como vecino).

Por qué UCS y no BFS / A*:
    * BFS minimiza el NÚMERO de pasos, pero aquí un paso por humo denso es mucho
      peor que uno por aire limpio: BFS puede atravesar humo para "ahorrar" pasos.
      (En los experimentos la ruta más corta en pasos tiene 30/38/78 pasos en B/C/D
      y la de UCS 32/40/90: UCS da algunos pasos más a cambio de menos riesgo.)
    * A* necesitaría una heurística admisible; el humo es arbitrario y no tenemos
      una estimación confiable. UCS = Dijkstra detenido al llegar a la meta; es
      óptimo y completo sin heurística.

Propiedades (por si las preguntan):
    * Completo: si hay ruta, la encuentra (los costos son >= 1, nunca 0).
    * Óptimo: porque la meta se prueba AL EXPANDIR, no al generar.
    * Complejidad: O(N log N) con N celdas (cada celda se expande una vez; cada
      inserción/extracción del heap cuesta log N). Memoria O(N).
    * Si no hay ruta: la frontera se vacía y se devuelve un Resultado sin ruta.
      Nunca hay bucle infinito porque cada celda se expande como máximo una vez.

Ejemplo mínimo (mapa 2x3, S=inicio en (0,0), G=meta en (0,2)):
        S  50  G          Arriba el camino directo cuesta 50 + 1 = 51.
        1   1  1          Por abajo: (1,0)=1, (1,1)=1, (1,2)=1, (0,2)=1 -> 4.
    UCS elige la de abajo (costo 4) aunque tenga más pasos. Ése es el punto.
=====================================================================================
"""
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

    Con varias salidas no hace falta correr una búsqueda por salida: la primera
    meta que sale del heap es, por construcción, la más barata de todas.
    """
    t0 = time.perf_counter()
    # El conjunto permite consultar en O(1) si una posición es meta.
    metas = set(escenario.metas)
    inicio = escenario.inicio

    # Un inicio bloqueado no permite comenzar la búsqueda.
    if not escenario.es_transitable(inicio):
        return _sin_ruta(0, [], t0)

    # --- Estructuras de datos (las 5 que hay que saber nombrar) ----------------
    # 1) frontera: min-heap de (costo acumulado, posición). heappop siempre saca
    #    el menor g. Al empatar, Python compara la posición (tupla): por eso el
    #    resultado es determinista (misma entrada -> misma ruta siempre).
    frontera: list[tuple[int, Posicion]] = [(0, inicio)]
    # 2) mejor_g: el menor costo encontrado hasta ahora para llegar a cada celda.
    mejor_g: dict[Posicion, int] = {inicio: 0}
    # 3) padre: de qué celda venimos; sirve para reconstruir la ruta al final.
    padre: dict[Posicion, Posicion | None] = {inicio: None}
    # 4) cerrados: celdas ya expandidas con su costo MÍNIMO definitivo.
    cerrados: set[Posicion] = set()
    # 5) orden: lista de celdas en el orden en que se expandieron. Es el "rastro"
    #    azul del mapa, la animación (--animar) y la métrica "nodos expandidos".
    orden: list[Posicion] = []

    while frontera:
        # PASO 1: sacar el pendiente más barato.
        g, estado = heapq.heappop(frontera)
        if estado in cerrados:
            # heapq no sabe "actualizar" una prioridad. Cuando se halla un camino
            # mejor a una celda se inserta OTRA entrada y la vieja queda dentro del
            # heap. Al salir la vieja, la celda ya está cerrada: se ignora.
            continue  # entrada obsoleta de la cola de prioridad

        # PASO 2: expandir = cerrar la celda y registrar el orden.
        cerrados.add(estado)
        orden.append(estado)

        # PASO 3: ¿es una salida? (prueba de meta AL EXPANDIR)
        # La meta se comprueba al expandir: con costos positivos, su costo ya
        # es mínimo al salir del heap. Comprobarla al generar podría aceptar
        # una ruta más cara antes de descubrir otra más barata.
        if estado in metas:
            ruta = _reconstruir(padre, estado)
            # Cuenta las celdas de la ruta cuyo costo alcanza el umbral de humo.
            humo = sum(1 for p in ruta if escenario.costo(p) >= UMBRAL_HUMO)
            return Resultado(tuple(ruta), g, len(orden), tuple(orden),
                             _ms(t0), humo)

        # PASO 4: generar sucesores (N, S, E, O) que estén en el mapa y no bloqueados.
        # Solo se generan vecinos dentro del mapa y que no estén bloqueados.
        for vecino in escenario.vecinos_transitables(estado):
            # El costo de un movimiento incluye el costo de entrar al vecino.
            nuevo_g = g + escenario.costo(vecino)
            # PASO 5 (relajación): solo se guarda si mejora lo que ya se conocía.
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
    # Se construyó de meta hacia inicio; se invierte para dejarla inicio → meta.
    return ruta[::-1]


# Convierte a milisegundos el tiempo transcurrido desde t0.
def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000


# Crea un resultado sin ruta y conserva las métricas de búsqueda
# (ruta=None, costo=None; los nodos expandidos aún sirven para el análisis).
def _sin_ruta(expandidos: int, orden: list[Posicion], t0: float) -> Resultado:
    return Resultado(None, None, expandidos, tuple(orden), _ms(t0))
