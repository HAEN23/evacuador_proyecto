"""Lectura y escritura de escenarios en CSV.

Formato:
    # start=r,c goal=r,c;r,c
    <matriz de enteros 0-99 separada por comas>
"""
from __future__ import annotations

import csv
from pathlib import Path

from .modelos import Escenario, Posicion


def guardar_csv(ruta: str | Path, escenario: Escenario) -> None:
    # Se usa ";" entre salidas porque la coma separa fila y columna.
    metas = ";".join(f"{r},{c}" for r, c in escenario.metas)
    # newline="" evita líneas en blanco adicionales en Windows con csv.
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        # La primera línea guarda inicio y salidas; el resto contiene la matriz.
        f.write(f"# start={escenario.inicio[0]},{escenario.inicio[1]} goal={metas}\n")
        csv.writer(f).writerows(escenario.grid)


def cargar_csv(ruta: str | Path) -> Escenario:
    with open(ruta, newline="", encoding="utf-8") as f:
        # La cabecera está en la primera línea; lo restante es la matriz CSV.
        cabecera = f.readline().strip()
        inicio, metas = _parsear_cabecera(cabecera)
        # Ignora filas vacías; int convierte cada valor y señala texto inválido.
        grid = [[int(v) for v in fila] for fila in csv.reader(f) if fila]
    # desde_listas crea el modelo y __post_init__ valida la cuadrícula.
    return Escenario.desde_listas(grid, inicio, metas)


def _parsear_cabecera(cabecera: str) -> tuple[Posicion, list[Posicion]]:
    if not cabecera.startswith("# start="):
        raise ValueError("Falta la cabecera '# start=r,c goal=r,c'")
    try:
        # Ejemplo: "# start=0,0 goal=11,19;5,5"; cada clave se separa por "=".
        partes = dict(p.split("=") for p in cabecera[2:].split())
        inicio = _pos(partes["start"])
        metas = [_pos(m) for m in partes["goal"].split(";")]
    except (KeyError, ValueError) as exc:
        # Unifica claves faltantes y formatos incorrectos en un mensaje claro.
        raise ValueError(f"Cabecera inválida: {cabecera!r}") from exc
    return inicio, metas


def _pos(texto: str) -> Posicion:
    r, c = texto.split(",")
    return int(r), int(c)
