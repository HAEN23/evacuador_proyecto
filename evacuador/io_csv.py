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
    metas = ";".join(f"{r},{c}" for r, c in escenario.metas)
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        f.write(f"# start={escenario.inicio[0]},{escenario.inicio[1]} goal={metas}\n")
        csv.writer(f).writerows(escenario.grid)


def cargar_csv(ruta: str | Path) -> Escenario:
    with open(ruta, newline="", encoding="utf-8") as f:
        cabecera = f.readline().strip()
        inicio, metas = _parsear_cabecera(cabecera)
        grid = [[int(v) for v in fila] for fila in csv.reader(f) if fila]
    return Escenario.desde_listas(grid, inicio, metas)


def _parsear_cabecera(cabecera: str) -> tuple[Posicion, list[Posicion]]:
    if not cabecera.startswith("# start="):
        raise ValueError("Falta la cabecera '# start=r,c goal=r,c'")
    try:
        partes = dict(p.split("=") for p in cabecera[2:].split())
        inicio = _pos(partes["start"])
        metas = [_pos(m) for m in partes["goal"].split(";")]
    except (KeyError, ValueError) as exc:
        raise ValueError(f"Cabecera inválida: {cabecera!r}") from exc
    return inicio, metas


def _pos(texto: str) -> Posicion:
    r, c = texto.split(",")
    return int(r), int(c)
