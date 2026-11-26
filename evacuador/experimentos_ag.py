"""Experimentos del AG y tablas de resultados (texto y CSV).

- Comparación justa AG vs salidas al azar vs búsqueda exhaustiva en los escenarios A–D.
- Tablas del mejor individuo por generación y comparativa del top 3, en Markdown y CSV.

No imprime ni escribe archivos: devuelve datos y texto. La salida la maneja cli.py.
"""
from __future__ import annotations

import csv
import io
import itertools
import math
import random
import statistics
from dataclasses import dataclass, replace

from .experimentos import construir_escenarios
from .genetico import (Configuracion, ParametrosAG, ProblemaAG, ResultadoAG, crear_problema,
                       decodificar, evaluar, optimizar, reparar)
from .io_grupos import generar_grupos
from .modelos import Escenario, Posicion

# Más combinaciones que esto y la búsqueda exhaustiva se rechaza (tardaría demasiado).
LIMITE_EXHAUSTIVO = 50_000
SEMILLAS_POR_DEFECTO = tuple(range(10))
# Grupos de los experimentos: los mismos que data/grupos_a.csv ... grupos_d.csv.
GRUPOS_N, GRUPOS_TAMANO_MAX, GRUPOS_SEMILLA = 12, 8, 1


# --- Líneas base -------------------------------------------------------------

def mejor_al_azar(problema: ProblemaAG, evaluaciones: int, semilla: int | None = None) -> float:
    """Mejor aptitud entre `evaluaciones` configuraciones distintas generadas al azar.

    Se usan genes al azar con la misma decodificación y reparación que el AG, para que
    la comparación sea justa. Se cuentan configuraciones distintas, igual que el AG.
    """
    if evaluaciones < 1:
        raise ValueError("Debe haber al menos una evaluación")
    rng = random.Random(semilla)
    vistas: set[tuple[Posicion, ...]] = set()
    mejor = 0.0
    # Tope de intentos por si el mapa tiene menos configuraciones distintas que las pedidas.
    for _ in range(20 * evaluaciones):
        if len(vistas) >= evaluaciones:
            break
        genes = [rng.random() for _ in range(2 * problema.k)]
        posiciones = reparar(decodificar(genes, problema.filas, problema.columnas),
                             problema.validas, problema.validas_set, problema.d_min)
        if posiciones is None:
            continue
        salidas = tuple(sorted(posiciones))
        if salidas not in vistas:
            vistas.add(salidas)
            mejor = max(mejor, evaluar(problema, salidas).aptitud)
    return mejor


def combinaciones_exhaustivas(problema: ProblemaAG) -> int:
    """Número de combinaciones de k celdas válidas (antes de filtrar por d_min)."""
    return math.comb(len(problema.validas), problema.k)


def busqueda_exhaustiva(problema: ProblemaAG,
                        limite: int = LIMITE_EXHAUSTIVO) -> Configuracion | None:
    """Evalúa todas las combinaciones válidas y devuelve la de mayor aptitud.

    Lanza ValueError si hay más de `limite` combinaciones. Devuelve None si ninguna
    combinación respeta d_min.
    """
    total = combinaciones_exhaustivas(problema)
    if total > limite:
        raise ValueError(f"Búsqueda exhaustiva demasiado grande: {total} combinaciones "
                         f"(límite {limite}). Use un mapa más pequeño o k = 2.")
    mejor: Configuracion | None = None
    for salidas in itertools.combinations(problema.validas, problema.k):
        if all(abs(a[0] - b[0]) + abs(a[1] - b[1]) >= problema.d_min
               for a, b in itertools.combinations(salidas, 2)):
            conf = evaluar(problema, salidas)
            if mejor is None or conf.aptitud > mejor.aptitud:
                mejor = conf
    return mejor


# --- Comparación AG vs azar vs exhaustivo ------------------------------------

@dataclass(frozen=True)
class FilaComparacion:
    """Resultado de comparar el AG con las líneas base en un escenario."""

    nombre: str
    dimensiones: str
    k: int
    semillas: int
    evaluaciones_media: float          # evaluaciones del AG; el azar usa las mismas
    ag_media: float
    ag_min: float
    ag_max: float
    azar_media: float
    azar_min: float
    azar_max: float
    exhaustivo: float | None           # None si el problema es demasiado grande


def comparar(nombre: str, escenario: Escenario, grupos, params: ParametrosAG = ParametrosAG(),
             semillas=SEMILLAS_POR_DEFECTO, exhaustivo: bool = True) -> FilaComparacion:
    """Corre el AG con cada semilla y el azar con el mismo número de evaluaciones.

    La búsqueda exhaustiva no depende de la semilla, así que se corre una sola vez y
    solo si no pasa de LIMITE_EXHAUSTIVO combinaciones.
    """
    semillas = tuple(semillas)
    if not semillas:
        raise ValueError("Debe haber al menos una semilla")
    problema = crear_problema(escenario, grupos, params)
    ag: list[float] = []
    azar: list[float] = []
    evaluaciones: list[int] = []
    for semilla in semillas:
        resultado = optimizar(escenario, grupos, replace(params, semilla=semilla))
        ag.append(resultado.mejor.aptitud)
        evaluaciones.append(resultado.evaluaciones)
        azar.append(mejor_al_azar(problema, resultado.evaluaciones, semilla))
    valor_ex = None
    if exhaustivo and combinaciones_exhaustivas(problema) <= LIMITE_EXHAUSTIVO:
        conf = busqueda_exhaustiva(problema)
        valor_ex = conf.aptitud if conf else 0.0
    return FilaComparacion(
        nombre=nombre, dimensiones=f"{escenario.filas}x{escenario.columnas}", k=params.k,
        semillas=len(semillas), evaluaciones_media=statistics.mean(evaluaciones),
        ag_media=statistics.mean(ag), ag_min=min(ag), ag_max=max(ag),
        azar_media=statistics.mean(azar), azar_min=min(azar), azar_max=max(azar),
        exhaustivo=valor_ex)


def comparar_todos(params: ParametrosAG = ParametrosAG(k=2), semillas=SEMILLAS_POR_DEFECTO,
                   exhaustivo: bool = True) -> list[FilaComparacion]:
    """Comparación en los escenarios A–D con los grupos de data/grupos_*.csv.

    El E (4x4 aislado) se omite: casi no tiene celdas donde colocar k salidas con d_min.
    """
    filas = []
    for nombre, esc in construir_escenarios()[:4]:
        grupos = generar_grupos(esc, GRUPOS_N, GRUPOS_TAMANO_MAX, GRUPOS_SEMILLA)
        filas.append(comparar(nombre, esc, grupos, params, semillas, exhaustivo))
    return filas


# --- Tablas ------------------------------------------------------------------

def _markdown(encabezado: tuple[str, ...], filas: list[tuple[str, ...]]) -> str:
    lineas = ["| " + " | ".join(encabezado) + " |",
              "|" + "|".join("---" for _ in encabezado) + "|"]
    lineas += ["| " + " | ".join(f) + " |" for f in filas]
    return "\n".join(lineas)


def _csv(encabezado: tuple[str, ...], filas: list[tuple[str, ...]]) -> str:
    salida = io.StringIO()
    escritor = csv.writer(salida, lineterminator="\n")
    escritor.writerow(encabezado)
    escritor.writerows(filas)
    return salida.getvalue().rstrip("\n")


def _salidas(conf: Configuracion) -> str:
    return " ".join(f"({f},{c})" for f, c in conf.salidas)


_ENC_COMPARACION = ("Escenario", "Tamaño", "k", "Semillas", "Evaluaciones",
                    "AG media", "AG mín", "AG máx", "Azar media", "Azar mín", "Azar máx",
                    "Exhaustivo")


def _celdas_comparacion(f: FilaComparacion) -> tuple[str, ...]:
    return (f.nombre, f.dimensiones, str(f.k), str(f.semillas), f"{f.evaluaciones_media:.1f}",
            f"{f.ag_media:.4f}", f"{f.ag_min:.4f}", f"{f.ag_max:.4f}",
            f"{f.azar_media:.4f}", f"{f.azar_min:.4f}", f"{f.azar_max:.4f}",
            "-" if f.exhaustivo is None else f"{f.exhaustivo:.4f}")


def tabla_markdown(filas: list[FilaComparacion]) -> str:
    return _markdown(_ENC_COMPARACION, [_celdas_comparacion(f) for f in filas])


def tabla_csv(filas: list[FilaComparacion]) -> str:
    return _csv(_ENC_COMPARACION, [_celdas_comparacion(f) for f in filas])


_ENC_HISTORIAL = ("Generación", "Salidas", "O1", "O2", "O3", "O4", "Aptitud mejor",
                  "Aptitud promedio", "Aptitud peor")


def _filas_historial(resultado: ResultadoAG, cada: int) -> list[tuple[str, ...]]:
    if cada < 1:
        raise ValueError("cada debe ser al menos 1")
    ultima = resultado.historial[-1].numero
    return [(str(g.numero), _salidas(g.mejor), f"{g.mejor.o1:.4f}", f"{g.mejor.o2:.4f}",
             f"{g.mejor.o3:.4f}", f"{g.mejor.o4:.4f}", f"{g.aptitud_mejor:.4f}",
             f"{g.aptitud_promedio:.4f}", f"{g.aptitud_peor:.4f}")
            for g in resultado.historial if g.numero % cada == 0 or g.numero == ultima]


def historial_markdown(resultado: ResultadoAG, cada: int = 1) -> str:
    """Mejor individuo por generación. Con `cada` > 1 se resume (siempre incluye la última)."""
    return _markdown(_ENC_HISTORIAL, _filas_historial(resultado, cada))


def historial_csv(resultado: ResultadoAG) -> str:
    """Mejor individuo de cada generación, completo, en CSV."""
    return _csv(_ENC_HISTORIAL, _filas_historial(resultado, 1))


_ENC_TOP3 = ("Puesto", "Salidas", "Personas que salen (%)", "Riesgo promedio por persona",
             "T50 (s)", "T90 (s)", "T100 (s)", "Aglomeración máx (personas)",
             "Personas por salida", "Aptitud", "Evaluaciones")


def _filas_top3(resultado: ResultadoAG) -> list[tuple[str, ...]]:
    return [(str(i), _salidas(c), f"{100 * c.o1:.1f}", f"{c.riesgo_promedio:.2f}",
             str(c.t50), str(c.t90), str(c.t100), str(c.aglomeracion_max),
             " ".join(map(str, c.personas_por_salida)), f"{c.aptitud:.4f}",
             str(resultado.evaluaciones))
            for i, c in enumerate(resultado.top3, start=1)]


def top3_markdown(resultado: ResultadoAG) -> str:
    """Tabla comparativa de las (hasta) tres mejores configuraciones."""
    return _markdown(_ENC_TOP3, _filas_top3(resultado))


def top3_csv(resultado: ResultadoAG) -> str:
    return _csv(_ENC_TOP3, _filas_top3(resultado))
