"""Experimentos reproducibles: corre UCS sobre varios escenarios y arma la tabla de resultados.

No imprime ni escribe archivos: devuelve datos y texto. La salida la maneja cli.py.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass

from .generador import ConfigGenerador, generar_escenario
from .modelos import Escenario
from .ucs import buscar_ucs

REPETICIONES_TIEMPO = 5  # el tiempo se reporta como mediana de varias corridas

# (nombre, configuración del generador). Con semilla fija los resultados se repiten.
CONFIGURACIONES: tuple[tuple[str, ConfigGenerador], ...] = (
    ("A. Sin humo", ConfigGenerador(12, 20, 0.15, focos_humo=0, seed=1)),
    ("B. Humo moderado", ConfigGenerador(12, 20, 0.15, focos_humo=3, radio_humo=5, seed=7)),
    ("C. Mucho humo", ConfigGenerador(15, 25, 0.15, focos_humo=8, radio_humo=6, seed=3)),
    ("D. Mapa grande", ConfigGenerador(40, 40, 0.20, focos_humo=10, radio_humo=6, seed=11)),
)


@dataclass(frozen=True)
class FilaResultado:
    nombre: str
    dimensiones: str
    encontrada: bool
    costo: int | None
    pasos: int
    celdas_humo: int
    nodos_expandidos: int
    tiempo_ms: float


def escenario_sin_ruta() -> Escenario:
    """Caso límite construido a mano: la salida queda aislada por una pared."""
    grid = [[1, 1, 1, 1],
            [1, 1, 1, 1],
            [0, 0, 0, 0],
            [1, 1, 1, 1]]
    return Escenario.desde_listas(grid, (0, 0), [(3, 3)])


def construir_escenarios() -> list[tuple[str, Escenario]]:
    escenarios = [(n, generar_escenario(cfg)) for n, cfg in CONFIGURACIONES]
    escenarios.append(("E. Sin ruta (aislado)", escenario_sin_ruta()))
    return escenarios


def ejecutar(nombre: str, escenario: Escenario,
             repeticiones: int = REPETICIONES_TIEMPO) -> FilaResultado:
    corridas = [buscar_ucs(escenario) for _ in range(max(1, repeticiones))]
    res = corridas[0]  # el algoritmo es determinista: todas dan lo mismo salvo el tiempo
    return FilaResultado(
        nombre=nombre,
        dimensiones=f"{escenario.filas}x{escenario.columnas}",
        encontrada=res.encontrada,
        costo=res.costo,
        pasos=res.pasos,
        celdas_humo=res.celdas_humo,
        nodos_expandidos=res.nodos_expandidos,
        tiempo_ms=statistics.median(c.tiempo_ms for c in corridas),
    )


def ejecutar_todos(escenarios: list[tuple[str, Escenario]] | None = None) -> list[FilaResultado]:
    return [ejecutar(n, e) for n, e in (escenarios or construir_escenarios())]


def slug(nombre: str) -> str:
    """'B. Humo moderado' -> 'humo_moderado' (para nombres de archivo)."""
    texto = nombre.split(".", 1)[-1].strip().lower()
    limpio = "".join(c if c.isalnum() else "_" for c in texto)
    return "_".join(p for p in limpio.split("_") if p)


_ENCABEZADO = ("Escenario", "Tamaño", "Costo", "Pasos", "Celdas con humo",
               "Nodos expandidos", "Tiempo (ms)")


def _celdas(f: FilaResultado) -> tuple[str, ...]:
    if not f.encontrada:
        return (f.nombre, f.dimensiones, "sin ruta", "-", "-",
                str(f.nodos_expandidos), f"{f.tiempo_ms:.3f}")
    return (f.nombre, f.dimensiones, str(f.costo), str(f.pasos), str(f.celdas_humo),
            str(f.nodos_expandidos), f"{f.tiempo_ms:.3f}")


def tabla_markdown(filas: list[FilaResultado]) -> str:
    lineas = ["| " + " | ".join(_ENCABEZADO) + " |",
              "|" + "|".join("---" for _ in _ENCABEZADO) + "|"]
    lineas += ["| " + " | ".join(_celdas(f)) + " |" for f in filas]
    return "\n".join(lineas)


def tabla_csv(filas: list[FilaResultado]) -> str:
    return "\n".join(",".join(c.replace(",", ";") for c in fila)
                     for fila in [_ENCABEZADO, *map(_celdas, filas)])
