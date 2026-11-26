"""Lectura, escritura y generación de catálogos de grupos de personas.

Formato CSV (una fila por grupo):
    fila,columna,tamano
    3,5,4
    10,2,1

No imprime: devuelve datos y lanza ValueError con mensajes claros. La salida la maneja cli.py.
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

from .config import BLOQUEADA
from .genetico import Grupo
from .modelos import Escenario

ENCABEZADO = ("fila", "columna", "tamano")


def guardar_grupos(ruta: str | Path, grupos: list[Grupo]) -> None:
    """Escribe los grupos en CSV con el encabezado fila,columna,tamano."""
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(ENCABEZADO)
        escritor.writerows((g.celda[0], g.celda[1], g.tamano) for g in grupos)


def cargar_grupos(ruta: str | Path) -> list[Grupo]:
    """Lee un CSV de grupos. Lanza ValueError si el formato no es válido.

    Que la celda quede dentro del mapa lo valida `crear_problema`, que sí conoce el escenario.
    """
    with open(ruta, newline="", encoding="utf-8") as f:
        filas = list(csv.reader(f))
    # Las líneas en blanco al final del archivo no cuentan como filas vacías.
    while filas and not any(c.strip() for c in filas[-1]):
        filas.pop()
    if not filas or tuple(c.strip().lower() for c in filas[0]) != ENCABEZADO:
        raise ValueError(f"{ruta}: falta el encabezado 'fila,columna,tamano'")
    if len(filas) == 1:
        raise ValueError(f"{ruta}: el archivo no tiene grupos")
    return [_parsear_fila(fila, numero, ruta) for numero, fila in enumerate(filas[1:], start=2)]


def _parsear_fila(fila: list[str], numero: int, ruta: str | Path) -> Grupo:
    if not any(c.strip() for c in fila):
        raise ValueError(f"{ruta}, línea {numero}: fila vacía")
    if len(fila) != 3:
        raise ValueError(f"{ruta}, línea {numero}: se esperaban 3 valores (fila,columna,tamano)")
    try:
        f, c, tamano = (int(v.strip()) for v in fila)
    except ValueError:
        raise ValueError(f"{ruta}, línea {numero}: valor no entero en {fila}") from None
    if f < 0 or c < 0:
        raise ValueError(f"{ruta}, línea {numero}: fila y columna no pueden ser negativas")
    if tamano < 1:
        raise ValueError(f"{ruta}, línea {numero}: el tamaño debe ser al menos 1")
    return Grupo((f, c), tamano)


def generar_grupos(escenario: Escenario, n: int = 12, tamano_max: int = 8,
                   semilla: int | None = None) -> list[Grupo]:
    """Coloca `n` grupos en celdas distintas que no sean muro, con tamaño 1..tamano_max.

    Con la misma semilla el resultado es el mismo.
    """
    if n < 1:
        raise ValueError("Debe haber al menos un grupo")
    if tamano_max < 1:
        raise ValueError("tamano_max debe ser al menos 1")
    libres = [(f, c) for f in range(escenario.filas) for c in range(escenario.columnas)
              if escenario.grid[f][c] != BLOQUEADA]
    if n > len(libres):
        raise ValueError(f"Solo hay {len(libres)} celdas transitables para {n} grupos")
    rng = random.Random(semilla)
    return [Grupo(celda, rng.randint(1, tamano_max)) for celda in rng.sample(libres, n)]
