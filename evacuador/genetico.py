"""Algoritmo genético para ubicar k salidas de emergencia (EvacuAG).

Núcleo sin interfaz: no importa tkinter ni gui. Reutiliza `buscar_ucs` como
evaluador de rutas y no modifica el resto del sistema.

Individuo: lista de 2k reales [x1, y1, ..., xk, yk], cada gen en [0, 1]
(la posición de maniobra de cada salida).

Modelo de evacuación: cada grupo se mueve como una sola entidad con un tamaño
(personas). Recorrer una casilla toma 1 segundo. El UCS elige la ruta de menor
riesgo y sobre esa ruta se mide el tiempo.

Aptitud:   O1 · 1/(1+O2) · 1/(1+O3) · 1/(1+O4)   (ver `evaluar`).
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from .modelos import Escenario, Posicion
from .ucs import buscar_ucs

# Valores de k permitidos por la propuesta (conjunto K).
K_PERMITIDOS = (2, 3, 4)
# Cantidad de configuraciones al azar y semilla fija con que se calculan R_ref y T_ref.
CONFIGS_REF = 30
SEMILLA_REF = 0
# Valor de celda libre y sin humo: solo ahí se puede colocar una salida.
CELDA_LIBRE = 1


# --- Datos de entrada y de salida -------------------------------------------

@dataclass(frozen=True)
class Grupo:
    """Un grupo de personas que se mueve como una sola entidad."""

    celda: Posicion
    tamano: int = 1

    def __post_init__(self) -> None:
        if self.tamano < 1:
            raise ValueError("El tamaño de un grupo debe ser al menos 1")


@dataclass(frozen=True)
class ParametrosAG:
    """Parámetros del algoritmo. Los valores por defecto son los de la propuesta."""

    tam_poblacion: int = 20
    p_cruza: float = 0.80
    p_mut_ind: float = 0.30
    p_mut_gen: float = 0.25
    sigma: float = 0.30       # ajustado en la tarea 13 (antes 0.10); ver docs/PLAN_AG.md
    torneo: int = 3
    elitismo: int = 2
    generaciones: int = 100
    k: int = 3
    d_min: int = 3
    p_evac: float = 0.90      # porcentaje de personas cuyo tiempo de salida se optimiza
    ventana: int = 5          # segundos que abarca una aglomeración
    separacion_top3: int = 3  # distancia mínima (Manhattan) para considerar distinta una configuración; 0 = sin filtro
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
        if not 0 < self.p_evac <= 1:
            raise ValueError("p_evac debe estar en (0, 1]")
        if self.ventana < 1:
            raise ValueError("ventana debe ser al menos 1 segundo")
        if self.separacion_top3 < 0:
            raise ValueError("separacion_top3 no puede ser negativa")
        for nombre in ("p_cruza", "p_mut_ind", "p_mut_gen"):
            if not 0 <= getattr(self, nombre) <= 1:
                raise ValueError(f"{nombre} debe estar en [0, 1]")


@dataclass(frozen=True)
class Configuracion:
    """Una ubicación de salidas ya evaluada con sus cuatro objetivos."""

    salidas: tuple[Posicion, ...]            # (fila, col), ordenadas
    o1: float                                # personas que salen / personas totales
    o2: float                                # riesgo promedio por persona / R_ref
    o3: float                                # T_p / T_ref
    o4: float                                # aglomeración máxima / personas que salen
    aptitud: float
    riesgo_promedio: float                   # por persona, sin normalizar
    riesgo_max: float                        # el del grupo con más riesgo (informativo)
    personas_por_salida: tuple[int, ...]     # mismo orden que `salidas`
    t50: int                                 # segundos hasta que sale el 50 %
    t90: int                                 # segundos hasta que sale el 90 %
    t100: int                                # segundos hasta que sale el último grupo
    aglomeracion_max: int                    # personas en la peor ventana de una salida
    # (segundo, fracción acumulada de las personas totales) cada vez que salen grupos
    curva_evacuacion: tuple[tuple[int, float], ...] = ()


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
    """Datos fijos del problema: escenario, grupos y constantes derivadas."""

    grid: tuple[tuple[int, ...], ...]
    grupos: tuple[Grupo, ...]
    validas: tuple[Posicion, ...]            # celdas con valor 1, en orden fila-columna
    validas_set: frozenset[Posicion]
    k: int
    d_min: int
    p_evac: float
    ventana: int
    r_ref: float
    t_ref: float

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


@dataclass(frozen=True)
class _Medidas:
    """Magnitudes físicas de unas salidas, antes de normalizar con R_ref y T_ref."""

    personas: int                            # personas que llegan a alguna salida
    riesgo_promedio: float
    riesgo_max: float
    t50: int
    t90: int
    t100: int
    t_p: int
    por_salida: tuple[int, ...]
    pico: int
    curva: tuple[tuple[int, float], ...]


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


# --- Medición y evaluación ---------------------------------------------------

def _tiempo_para(ordenadas: list[tuple[int, int, int, int]], personas: int, p: float) -> int:
    """Primer segundo en que ya salió el p % de las personas que llegan a una salida.

    `ordenadas` son las llegadas (tiempo, salida, tamaño, riesgo) por tiempo creciente.
    """
    umbral = p * personas
    acumuladas = 0
    for tiempo, _, tamano, _ in ordenadas:
        acumuladas += tamano
        if acumuladas >= umbral - 1e-9:
            return tiempo
    return ordenadas[-1][0]


def _pico_ventana(llegadas: list[tuple[int, int]], ventana: int) -> int:
    """Máximo de personas que llegan a una salida dentro de una ventana de `ventana` s.

    `llegadas` son (tiempo, tamaño). La ventana [t, t + ventana) arranca en cada llegada.
    """
    if not llegadas:
        return 0
    return max(sum(tam for t, tam in llegadas if inicio <= t < inicio + ventana)
               for inicio, _ in llegadas)


def _medir(problema: ProblemaAG, salidas: tuple[Posicion, ...]) -> _Medidas | None:
    """Evalúa físicamente unas salidas. None si ningún grupo llega a una salida.

    Un solo UCS por grupo: `metas` son todas las salidas y UCS devuelve la de menor
    riesgo acumulado (la meta del último nodo de la ruta). El tiempo es el número
    de pasos de esa ruta: cada casilla recorrida cuesta 1 segundo.
    """
    llegadas: list[tuple[int, int, int, int]] = []
    indice = {s: i for i, s in enumerate(salidas)}
    for grupo in problema.grupos:
        resultado = buscar_ucs(Escenario(problema.grid, grupo.celda, salidas))
        if resultado.encontrada:
            llegadas.append((resultado.pasos, indice[resultado.ruta[-1]],
                             grupo.tamano, resultado.costo))
    if not llegadas:
        return None

    ordenadas = sorted(llegadas)
    personas = sum(tam for _, _, tam, _ in llegadas)
    total = sum(g.tamano for g in problema.grupos)
    por_salida = tuple(sum(tam for _, s, tam, _ in llegadas if s == i)
                       for i in range(len(salidas)))
    pico = max(_pico_ventana([(t, tam) for t, s, tam, _ in llegadas if s == i],
                             problema.ventana) for i in range(len(salidas)))

    curva: list[tuple[int, float]] = []
    acumuladas = 0
    for tiempo, _, tamano, _ in ordenadas:
        acumuladas += tamano
        if curva and curva[-1][0] == tiempo:
            curva[-1] = (tiempo, acumuladas / total)
        else:
            curva.append((tiempo, acumuladas / total))

    return _Medidas(
        personas=personas,
        riesgo_promedio=sum(tam * riesgo for _, _, tam, riesgo in llegadas) / personas,
        riesgo_max=float(max(riesgo for _, _, _, riesgo in llegadas)),
        t50=_tiempo_para(ordenadas, personas, 0.5),
        t90=_tiempo_para(ordenadas, personas, 0.9),
        t100=ordenadas[-1][0],
        t_p=_tiempo_para(ordenadas, personas, problema.p_evac),
        por_salida=por_salida,
        pico=pico,
        curva=tuple(curva),
    )


def evaluar(problema: ProblemaAG, salidas: tuple[Posicion, ...]) -> Configuracion:
    """Calcula O1..O4 y la aptitud de unas salidas ya válidas.

    O1 = personas que salen / personas totales
    O2 = riesgo promedio por persona / R_ref
    O3 = T_p / T_ref        (T_p: segundos hasta que sale el p % de las personas)
    O4 = personas en la peor ventana de una salida / personas que salen
    Sin ningún grupo con ruta: O1 = 0, O2 = O3 = O4 = 0 y aptitud 0.
    """
    salidas = tuple(sorted(salidas))
    medidas = _medir(problema, salidas)
    if medidas is None:
        return Configuracion(salidas, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
                             (0,) * len(salidas), 0, 0, 0, 0)
    total = sum(g.tamano for g in problema.grupos)
    o1 = medidas.personas / total
    o2 = medidas.riesgo_promedio / problema.r_ref
    o3 = medidas.t_p / problema.t_ref
    o4 = medidas.pico / medidas.personas
    aptitud = o1 * (1 / (1 + o2)) * (1 / (1 + o3)) * (1 / (1 + o4))
    return Configuracion(salidas, o1, o2, o3, o4, aptitud, medidas.riesgo_promedio,
                         medidas.riesgo_max, medidas.por_salida, medidas.t50, medidas.t90,
                         medidas.t100, medidas.pico, medidas.curva)


# --- Construcción del problema y referencias ---------------------------------

def _como_grupo(dato) -> Grupo:
    """Acepta Grupo, (fila, col) o (fila, col, tamaño)."""
    if isinstance(dato, Grupo):
        return dato
    dato = tuple(dato)
    if len(dato) == 2:
        return Grupo((dato[0], dato[1]))
    if len(dato) == 3:
        return Grupo((dato[0], dato[1]), dato[2])
    raise ValueError(f"Grupo inválido: {dato}")


def crear_problema(escenario: Escenario, grupos, params: ParametrosAG) -> ProblemaAG:
    """Valida los datos y calcula R_ref y T_ref una sola vez para el escenario.

    Del escenario solo se usa la cuadrícula; su inicio y sus metas se ignoran.
    """
    grupos = tuple(_como_grupo(g) for g in grupos)
    if not grupos:
        raise ValueError("Debe haber al menos un grupo")
    for grupo in grupos:
        if not escenario.dentro(grupo.celda):
            raise ValueError(f"Grupo fuera de la cuadrícula: {grupo.celda}")
    validas = tuple((f, c) for f in range(escenario.filas) for c in range(escenario.columnas)
                    if escenario.grid[f][c] == CELDA_LIBRE)
    if len(validas) < params.k:
        raise ValueError("No hay celdas libres suficientes para colocar las salidas")

    base = ProblemaAG(escenario.grid, grupos, validas, frozenset(validas), params.k,
                      params.d_min, params.p_evac, params.ventana, 1.0, 1.0)
    r_ref, t_ref = _calcular_referencias(base)
    return ProblemaAG(escenario.grid, grupos, validas, frozenset(validas), params.k,
                      params.d_min, params.p_evac, params.ventana, r_ref, t_ref)


def _calcular_referencias(problema: ProblemaAG) -> tuple[float, float]:
    """R_ref y T_ref: promedio de 30 configuraciones al azar con semilla fija.

    R_ref es el riesgo promedio por persona y T_ref el tiempo T_p. Solo cuentan
    grupos con ruta. Si no hay ninguna medición útil (o el valor es 0) se usa 1.0
    para evitar divisiones por cero.
    """
    rng = random.Random(SEMILLA_REF)
    riesgos: list[float] = []
    tiempos: list[float] = []
    for _ in range(CONFIGS_REF):
        genes = [rng.random() for _ in range(2 * problema.k)]
        posiciones = reparar(decodificar(genes, problema.filas, problema.columnas),
                             problema.validas, problema.validas_set, problema.d_min)
        if posiciones is None:
            continue
        medidas = _medir(problema, tuple(sorted(posiciones)))
        if medidas is not None:
            riesgos.append(medidas.riesgo_promedio)
            tiempos.append(medidas.t_p)
    r_ref = sum(riesgos) / len(riesgos) if riesgos else 1.0
    t_ref = sum(tiempos) / len(tiempos) if tiempos else 1.0
    return (r_ref if r_ref > 0 else 1.0), (t_ref if t_ref > 0 else 1.0)


# --- Bucle del algoritmo genético --------------------------------------------

# Configuración de un individuo que no se pudo reparar: aptitud 0.
_INVALIDA = Configuracion((), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, (), 0, 0, 0, 0)


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


def _parecidas(a: tuple[Posicion, ...], b: tuple[Posicion, ...], separacion: int) -> bool:
    """Dos configuraciones son parecidas si cada salida de `a` está a `separacion` casillas
    o menos (Manhattan) de alguna salida de `b`. Con separacion 0 solo lo son las idénticas."""
    return all(any(abs(f - g) + abs(c - h) <= separacion for g, h in b) for f, c in a)


def _elegir_top3(candidatas: list[Configuracion], separacion: int) -> list[Configuracion]:
    """Toma las mejores configuraciones que no se parezcan a otra ya elegida."""
    elegidas: list[Configuracion] = []
    for cand in candidatas:
        if all(not _parecidas(cand.salidas, e.salidas, separacion)
               and not _parecidas(e.salidas, cand.salidas, separacion) for e in elegidas):
            elegidas.append(cand)
            if len(elegidas) == 3:
                break
    return elegidas


def optimizar(escenario: Escenario, grupos, params: ParametrosAG = ParametrosAG()) -> ResultadoAG:
    """Busca las posiciones de k salidas con mayor aptitud.

    `grupos` es una lista de Grupo, (fila, col) o (fila, col, tamaño).
    Con la misma semilla y los mismos datos el resultado es idéntico.
    El historial incluye la generación 0 (población inicial) y las `generaciones`
    siguientes. `top3` recoge las 3 mejores configuraciones de toda la corrida que no se parezcan
    entre sí (ver `ParametrosAG.separacion_top3`); puede traer menos de 3 si no hay más.
    """
    rng = random.Random(params.semilla)
    problema = crear_problema(escenario, grupos, params)
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
    top3 = tuple(_elegir_top3(candidatas, params.separacion_top3)) or (_INVALIDA,)
    return ResultadoAG(top3, tuple(historial), len(evaluador.cache))
