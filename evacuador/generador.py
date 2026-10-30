"""Generador de escenarios reproducibles (parametrizable y con semilla)."""
from __future__ import annotations

import random
from dataclasses import dataclass

from .config import BLOQUEADA, COSTO_MAX, COSTO_MIN
from .modelos import Escenario
from .ucs import buscar_ucs


@dataclass(frozen=True)
class ConfigGenerador:
    filas: int = 15
    columnas: int = 25
    densidad_bloqueo: float = 0.15   # fracción de celdas bloqueadas
    focos_humo: int = 3
    radio_humo: int = 5              # alcance del humo desde cada foco
    seed: int | None = None
    garantizar_ruta: bool = True
    max_intentos: int = 200

    def __post_init__(self) -> None:
        if self.filas < 2 or self.columnas < 2:
            raise ValueError("La cuadrícula mínima es 2x2")
        if not 0 <= self.densidad_bloqueo < 1:
            raise ValueError("densidad_bloqueo debe estar en [0, 1)")


def generar_escenario(cfg: ConfigGenerador = ConfigGenerador()) -> Escenario:
    """Crea un escenario con humo que decae con la distancia a cada foco."""
    rng = random.Random(cfg.seed)
    inicio = (0, 0)
    meta = (cfg.filas - 1, cfg.columnas - 1)

    for _ in range(cfg.max_intentos):
        grid = [[COSTO_MIN] * cfg.columnas for _ in range(cfg.filas)]
        _colocar_humo(grid, cfg, rng)
        _colocar_bloqueos(grid, cfg, rng)
        grid[inicio[0]][inicio[1]] = COSTO_MIN
        grid[meta[0]][meta[1]] = COSTO_MIN

        escenario = Escenario.desde_listas(grid, inicio, [meta])
        if not cfg.garantizar_ruta or buscar_ucs(escenario).encontrada:
            return escenario

    raise RuntimeError("No se logró generar un escenario resoluble; "
                       "reduzca la densidad de bloqueo.")


def _colocar_humo(grid: list[list[int]], cfg: ConfigGenerador, rng: random.Random) -> None:
    rango = COSTO_MAX - COSTO_MIN
    for _ in range(cfg.focos_humo):
        fr, fc = rng.randrange(cfg.filas), rng.randrange(cfg.columnas)
        for r in range(cfg.filas):
            for c in range(cfg.columnas):
                d = abs(r - fr) + abs(c - fc)
                if d <= cfg.radio_humo:
                    valor = int(COSTO_MAX - rango * d / (cfg.radio_humo + 1))
                    grid[r][c] = max(grid[r][c], valor)


def _colocar_bloqueos(grid: list[list[int]], cfg: ConfigGenerador, rng: random.Random) -> None:
    for r in range(cfg.filas):
        for c in range(cfg.columnas):
            if rng.random() < cfg.densidad_bloqueo:
                grid[r][c] = BLOQUEADA
