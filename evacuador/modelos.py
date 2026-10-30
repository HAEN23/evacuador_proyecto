"""Modelos de datos inmutables: el escenario (entorno) y el resultado de la búsqueda."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Sequence

from .config import BLOQUEADA, COSTO_MAX, MOVIMIENTOS

Posicion = tuple[int, int]


@dataclass(frozen=True)
class Escenario:
    """Cuadrícula estática. Cada celda vale 0 (bloqueada) o 1..99 (costo de riesgo)."""

    grid: tuple[tuple[int, ...], ...]
    inicio: Posicion
    metas: tuple[Posicion, ...]

    def __post_init__(self) -> None:
        if not self.grid or not self.grid[0]:
            raise ValueError("La cuadrícula no puede estar vacía")
        if any(len(fila) != len(self.grid[0]) for fila in self.grid):
            raise ValueError("La matriz no es rectangular")
        if any(not (BLOQUEADA <= v <= COSTO_MAX) for f in self.grid for v in f):
            raise ValueError(f"Hay valores fuera del rango {BLOQUEADA}-{COSTO_MAX}")
        if not self.metas:
            raise ValueError("Debe existir al menos una salida")
        for pos in (self.inicio, *self.metas):
            if not self.dentro(pos):
                raise ValueError(f"Posición fuera de la cuadrícula: {pos}")

    @classmethod
    def desde_listas(cls, grid: Sequence[Sequence[int]], inicio: Posicion,
                     metas: Sequence[Posicion]) -> "Escenario":
        return cls(tuple(tuple(f) for f in grid), tuple(inicio), tuple(map(tuple, metas)))

    @property
    def filas(self) -> int:
        return len(self.grid)

    @property
    def columnas(self) -> int:
        return len(self.grid[0])

    def dentro(self, pos: Posicion) -> bool:
        return 0 <= pos[0] < self.filas and 0 <= pos[1] < self.columnas

    def costo(self, pos: Posicion) -> int:
        return self.grid[pos[0]][pos[1]]

    def es_transitable(self, pos: Posicion) -> bool:
        return self.costo(pos) != BLOQUEADA

    def vecinos_transitables(self, pos: Posicion) -> Iterator[Posicion]:
        """Valida transitabilidad ANTES de que el costo entre en juego."""
        for dr, dc in MOVIMIENTOS:
            vecino = (pos[0] + dr, pos[1] + dc)
            if self.dentro(vecino) and self.es_transitable(vecino):
                yield vecino


@dataclass(frozen=True)
class Resultado:
    """Salida de la búsqueda: solución y métricas de rendimiento."""

    ruta: tuple[Posicion, ...] | None
    costo: int | None
    nodos_expandidos: int
    explorados: tuple[Posicion, ...]   # en orden de expansión
    tiempo_ms: float
    celdas_humo: int = 0

    @property
    def encontrada(self) -> bool:
        return self.ruta is not None

    @property
    def pasos(self) -> int:
        return len(self.ruta) - 1 if self.ruta else 0
