"""Algoritmo genético para ubicar k salidas de emergencia (EvacuAG).

Núcleo sin interfaz: no importa tkinter ni gui. Reutiliza `buscar_ucs` como
evaluador de rutas y no modifica el resto del sistema.

Individuo: lista de 2k reales [x1, y1, ..., xk, yk], cada gen en [0, 1].
Aptitud:   O1 · 1/(1+O2) · 1/(1+O3) · 1/(1+O4)   (ver `evaluar`).
"""
from __future__ import annotations

import random
import statistics
from dataclasses import dataclass

from .modelos import Escenario, Posicion
from .ucs import buscar_ucs

# Valores de k permitidos por la propuesta (conjunto K).
K_PERMITIDOS = (2, 3, 4)
# Cantidad de configuraciones al azar y semilla fija con que se calcula R_ref.
CONFIGS_R_REF = 30
SEMILLA_R_REF = 0
# Valor de celda libre y sin humo: solo ahí se puede colocar una salida.
CELDA_LIBRE = 1


# --- Datos de entrada y de salida -------------------------------------------

@dataclass(frozen=True)
class ParametrosAG:
    """Parámetros del algoritmo. Los valores por defecto son los de la propuesta."""

    tam_poblacion: int = 20
    p_cruza: float = 0.80
    p_mut_ind: float = 0.30
    p_mut_gen: float = 0.25
    sigma: float = 0.10
    torneo: int = 3
    elitismo: int = 2
    generaciones: int = 100
    k: int = 3
    d_min: int = 3
    semilla: int | None = None

    def __post_init__(self) -> None:
        if self.k not in K_PERMITIDOS:
            raise ValueError(f"k debe estar en {K_PERMITIDOS}")
        if self.tam_poblacion < 2:
            raise ValueError("La población debe tener al menos 2 individuos")
        if not 0 <= self.elitismo < self.tam_poblacion:
            raise ValueError("elitismo debe estar en [0, tam_poblacion)")
        if not 1 <= self.torneo <= self.tam_poblacion:
            raise ValueError("torneo debe estar en [1, tam_poblacion]")
        if self.generaciones < 1:
            raise ValueError("Debe haber al menos una generación")
        if self.d_min < 1:
            raise ValueError("d_min debe ser al menos 1")
        if self.sigma <= 0:
            raise ValueError("sigma debe ser positivo")
        for nombre in ("p_cruza", "p_mut_ind", "p_mut_gen"):
            if not 0 <= getattr(self, nombre) <= 1:
                raise ValueError(f"{nombre} debe estar en [0, 1]")


@dataclass(frozen=True)
class Configuracion:
    """Una ubicación de salidas ya evaluada con sus cuatro objetivos."""

    salidas: tuple[Posicion, ...]            # (fila, col), ordenadas
    o1: float                                # cobertura, en [0, 1]
    o2: float                                # riesgo promedio / R_ref
    o3: float                                # riesgo máximo / R_ref
    o4: float                                # desbalance, en [0, sqrt(k-1)]
    aptitud: float
    riesgo_promedio: float
    riesgo_max: float
    ocupantes_por_salida: tuple[int, ...]    # mismo orden que `salidas`


@dataclass(frozen=True)
class Generacion:
    """Resumen de una generación. La 0 es la población inicial."""

    numero: int
    mejor: Configuracion
    aptitud_mejor: float
    aptitud_promedio: float
    aptitud_peor: float


@dataclass(frozen=True)
class ResultadoAG:
    top3: tuple[Configuracion, ...]          # hasta 3 distintas, de mayor a menor aptitud
    historial: tuple[Generacion, ...]        # generaciones 0..n
    evaluaciones: int                        # configuraciones distintas evaluadas con UCS

    @property
    def mejor(self) -> Configuracion:
        return self.top3[0]


@dataclass(frozen=True)
class ProblemaAG:
    """Datos fijos del problema: escenario, ocupantes y constantes derivadas."""

    grid: tuple[tuple[int, ...], ...]
    ocupantes: tuple[Posicion, ...]
    validas: tuple[Posicion, ...]            # celdas con valor 1, en orden fila-columna
    validas_set: frozenset[Posicion]
    k: int
    d_min: int
    r_ref: float

    @property
    def filas(self) -> int:
        return len(self.grid)

    @property
    def columnas(self) -> int:
        return len(self.grid[0])


@dataclass(frozen=True)
class _Individuo:
    genes: tuple[float, ...]
    conf: Configuracion

    @property
    def aptitud(self) -> float:
        return self.conf.aptitud


# Configuración de un individuo que no se pudo reparar: aptitud 0.
_INVALIDA = Configuracion((), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, ())


# --- Cromosoma: decodificación y reparación ---------------------------------

def decodificar(genes: tuple[float, ...] | list[float], filas: int, columnas: int) -> list[Posicion]:
    """Convierte [x1, y1, ...] en celdas (fila, col). Redondeo clásico (0.5 sube)."""
    return [(int(genes[i + 1] * (filas - 1) + 0.5), int(genes[i] * (columnas - 1) + 0.5))
            for i in range(0, len(genes), 2)]


def codificar(posiciones: list[Posicion], filas: int, columnas: int) -> tuple[float, ...]:
    """Operación inversa de `decodificar`: celdas a genes normalizados en [0, 1]."""
    genes: list[float] = []
    for fila, col in posiciones:
        genes.append(col / (columnas - 1) if columnas > 1 else 0.0)
        genes.append(fila / (filas - 1) if filas > 1 else 0.0)
    return tuple(genes)


def _lejos(pos: Posicion, colocadas: list[Posicion], d_min: int) -> bool:
    """True si `pos` está al menos a d_min (distancia Manhattan) de todas las colocadas."""
    return all(abs(pos[0] - c[0]) + abs(pos[1] - c[1]) >= d_min for c in colocadas)


def reparar(posiciones: list[Posicion], validas: tuple[Posicion, ...],
            validas_set: frozenset[Posicion], d_min: int) -> list[Posicion] | None:
    """Mueve cada salida a la celda válida más cercana que cumpla las restricciones.

    Se procesa en orden. Una salida ya válida y lo bastante lejos de las anteriores
    no se mueve. Con empate de distancia gana la celda menor en orden fila-columna.
    Devuelve None si alguna salida no tiene dónde ir (el individuo valdrá 0).
    """
    colocadas: list[Posicion] = []
    for pos in posiciones:
        if pos in validas_set and _lejos(pos, colocadas, d_min):
            colocadas.append(pos)
            continue
        mejor: tuple[int, Posicion] | None = None
        for candidata in validas:
            if not _lejos(candidata, colocadas, d_min):
                continue
            distancia = abs(candidata[0] - pos[0]) + abs(candidata[1] - pos[1])
            if mejor is None or distancia < mejor[0]:
                mejor = (distancia, candidata)
        if mejor is None:
            return None
        colocadas.append(mejor[1])
    return colocadas


# --- Evaluación --------------------------------------------------------------

def _rutas(grid: tuple[tuple[int, ...], ...], ocupantes: tuple[Posicion, ...],
           salidas: tuple[Posicion, ...]) -> tuple[list[int], list[int]]:
    """Riesgo de cada ocupante con ruta y cuántos ocupantes atiende cada salida.

    Un solo UCS por ocupante: `metas` son todas las salidas y UCS devuelve la
    de menor riesgo acumulado (la meta del último nodo de la ruta).
    """
    riesgos: list[int] = []
    conteo = {s: 0 for s in salidas}
    for ocupante in ocupantes:
        resultado = buscar_ucs(Escenario(grid, ocupante, salidas))
        if resultado.encontrada:
            riesgos.append(resultado.costo)
            conteo[resultado.ruta[-1]] += 1
    return riesgos, [conteo[s] for s in salidas]


def evaluar(problema: ProblemaAG, salidas: tuple[Posicion, ...]) -> Configuracion:
    """Calcula O1..O4 y la aptitud de unas salidas ya válidas.

    O1 = N_ruta / N
    O2 = riesgo promedio / R_ref        O3 = riesgo máximo / R_ref
    O4 = sigma(ocupantes por salida) / (N_ruta / k)
    Sin ocupantes con ruta: O1 = 0, O2 = O3 = O4 = 0 y aptitud 0.
    """
    salidas = tuple(sorted(salidas))
    riesgos, por_salida = _rutas(problema.grid, problema.ocupantes, salidas)
    if not riesgos:
        return Configuracion(salidas, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, tuple(por_salida))
    n_ruta = len(riesgos)
    promedio = sum(riesgos) / n_ruta
    maximo = max(riesgos)
    o1 = n_ruta / len(problema.ocupantes)
    o2 = promedio / problema.r_ref
    o3 = maximo / problema.r_ref
    # Desviación poblacional: el máximo es sqrt(k-1) (todos en una sola salida).
    o4 = statistics.pstdev(por_salida) / (n_ruta / problema.k)
    aptitud = o1 * (1 / (1 + o2)) * (1 / (1 + o3)) * (1 / (1 + o4))
    return Configuracion(salidas, o1, o2, o3, o4, aptitud, promedio, float(maximo),
                         tuple(por_salida))


# --- Construcción del problema y R_ref ---------------------------------------

def crear_problema(escenario: Escenario, ocupantes, params: ParametrosAG) -> ProblemaAG:
    """Valida los datos y calcula R_ref una sola vez para el escenario.

    Del escenario solo se usa la cuadrícula; su inicio y sus metas se ignoran.
    """
    ocupantes = tuple(tuple(o) for o in ocupantes)
    if not ocupantes:
        raise ValueError("Debe haber al menos un ocupante")
    for ocupante in ocupantes:
        if not escenario.dentro(ocupante):
            raise ValueError(f"Ocupante fuera de la cuadrícula: {ocupante}")
    validas = tuple((f, c) for f in range(escenario.filas) for c in range(escenario.columnas)
                    if escenario.grid[f][c] == CELDA_LIBRE)
    if len(validas) < params.k:
        raise ValueError("No hay celdas libres suficientes para colocar las salidas")

    base = ProblemaAG(escenario.grid, ocupantes, validas, frozenset(validas),
                      params.k, params.d_min, 1.0)
    return ProblemaAG(escenario.grid, ocupantes, validas, frozenset(validas),
                      params.k, params.d_min, _calcular_r_ref(base))


def _calcular_r_ref(problema: ProblemaAG) -> float:
    """Riesgo promedio con k salidas al azar: media de 30 configuraciones, semilla fija.

    Solo cuentan ocupantes con ruta. Si no hay ninguna medición útil (o el riesgo
    es 0) se usa 1.0 para evitar divisiones por cero.
    """
    rng = random.Random(SEMILLA_R_REF)
    medias: list[float] = []
    for _ in range(CONFIGS_R_REF):
        genes = [rng.random() for _ in range(2 * problema.k)]
        posiciones = reparar(decodificar(genes, problema.filas, problema.columnas),
                             problema.validas, problema.validas_set, problema.d_min)
        if posiciones is None:
            continue
        riesgos, _ = _rutas(problema.grid, problema.ocupantes, tuple(sorted(posiciones)))
        if riesgos:
            medias.append(sum(riesgos) / len(riesgos))
    r_ref = sum(medias) / len(medias) if medias else 1.0
    return r_ref if r_ref > 0 else 1.0


# --- Bucle del algoritmo genético --------------------------------------------

class _Evaluador:
    """Evalúa individuos con caché por configuración de salidas (el orden no importa)."""

    def __init__(self, problema: ProblemaAG) -> None:
        self.problema = problema
        self.cache: dict[tuple[Posicion, ...], Configuracion] = {}

    def individuo(self, genes: list[float] | tuple[float, ...]) -> _Individuo:
        p = self.problema
        posiciones = reparar(decodificar(genes, p.filas, p.columnas),
                             p.validas, p.validas_set, p.d_min)
        if posiciones is None:
            return _Individuo(tuple(genes), _INVALIDA)
        # El individuo guarda los genes ya reparados.
        reparados = codificar(posiciones, p.filas, p.columnas)
        clave = tuple(sorted(posiciones))
        if clave not in self.cache:
            self.cache[clave] = evaluar(p, clave)
        return _Individuo(reparados, self.cache[clave])


def _torneo(poblacion: list[_Individuo], tam: int, rng: random.Random) -> _Individuo:
    """Selección por torneo: gana el más apto de `tam` individuos sin repetir."""
    return max(rng.sample(poblacion, tam), key=lambda i: i.aptitud)


def _cruzar(a: _Individuo, b: _Individuo, rng: random.Random) -> list[float]:
    """Cruza aritmética: h = alfa·p1 + (1 - alfa)·p2, con alfa aleatorio en [0, 1]."""
    alfa = rng.random()
    return [alfa * x + (1 - alfa) * y for x, y in zip(a.genes, b.genes)]


def _mutar(genes: list[float], params: ParametrosAG, rng: random.Random) -> list[float]:
    """Mutación gaussiana por gen, recortada a [0, 1]. Se aplica con P_mut,ind."""
    if rng.random() >= params.p_mut_ind:
        return genes
    return [min(1.0, max(0.0, g + rng.gauss(0.0, params.sigma)))
            if rng.random() < params.p_mut_gen else g
            for g in genes]


def _resumen(numero: int, poblacion: list[_Individuo]) -> Generacion:
    aptitudes = [i.aptitud for i in poblacion]
    mejor = max(poblacion, key=lambda i: i.aptitud)
    return Generacion(numero, mejor.conf, mejor.aptitud,
                      sum(aptitudes) / len(aptitudes), min(aptitudes))


def optimizar(escenario: Escenario, ocupantes, params: ParametrosAG = ParametrosAG()) -> ResultadoAG:
    """Busca las posiciones de k salidas con mayor aptitud.

    Con la misma semilla y los mismos datos el resultado es idéntico.
    El historial incluye la generación 0 (población inicial) y las `generaciones`
    siguientes. `top3` recoge las 3 mejores configuraciones distintas de toda la corrida.
    """
    rng = random.Random(params.semilla)
    problema = crear_problema(escenario, ocupantes, params)
    evaluador = _Evaluador(problema)

    poblacion = [evaluador.individuo([rng.random() for _ in range(2 * params.k)])
                 for _ in range(params.tam_poblacion)]
    historial = [_resumen(0, poblacion)]

    for numero in range(1, params.generaciones + 1):
        # Elitismo: los mejores pasan intactos a la siguiente generación.
        ordenada = sorted(poblacion, key=lambda i: i.aptitud, reverse=True)
        nueva = ordenada[:params.elitismo]
        while len(nueva) < params.tam_poblacion:
            p1 = _torneo(poblacion, params.torneo, rng)
            if rng.random() < params.p_cruza:
                hijo = _cruzar(p1, _torneo(poblacion, params.torneo, rng), rng)
            else:
                hijo = list(p1.genes)
            nueva.append(evaluador.individuo(_mutar(hijo, params, rng)))
        poblacion = nueva
        historial.append(_resumen(numero, poblacion))

    # Empates de aptitud: se desempata por las salidas para que sea determinista.
    candidatas = sorted(evaluador.cache.values(), key=lambda c: (-c.aptitud, c.salidas))
    top3 = tuple(candidatas[:3]) or (_INVALIDA,)
    return ResultadoAG(top3, tuple(historial), len(evaluador.cache))
