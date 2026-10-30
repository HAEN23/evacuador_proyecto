"""Interfaz de línea de comandos."""
from __future__ import annotations

import argparse
import sys

from . import visualizacion as vis
from .generador import ConfigGenerador, generar_escenario
from .io_csv import cargar_csv, guardar_csv
from .ucs import buscar_ucs


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="evacuador",
                                description="Evacuación segura con búsqueda de costo uniforme (UCS)")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generar", help="genera un escenario y lo guarda en CSV")
    g.add_argument("salida")
    g.add_argument("--filas", type=int, default=15)
    g.add_argument("--cols", type=int, default=25)
    g.add_argument("--densidad", type=float, default=0.15, help="fracción de celdas bloqueadas")
    g.add_argument("--focos", type=int, default=3, help="número de focos de humo")
    g.add_argument("--radio", type=int, default=5, help="alcance del humo")
    g.add_argument("--seed", type=int, default=None)

    s = sub.add_parser("resolver", help="carga un CSV y calcula la ruta con UCS")
    s.add_argument("entrada")
    s.add_argument("--animar", action="store_true", help="muestra la exploración paso a paso")
    s.add_argument("--pausa", type=float, default=0.05)
    s.add_argument("--grafico", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.cmd == "generar":
            cfg = ConfigGenerador(args.filas, args.cols, args.densidad,
                                  args.focos, args.radio, args.seed)
            guardar_csv(args.salida, generar_escenario(cfg))
            print(f"Escenario guardado en {args.salida}")
        else:
            esc = cargar_csv(args.entrada)
            res = buscar_ucs(esc)
            if args.animar:
                vis.animar(esc, res, args.pausa)
            vis.mostrar_resultado(esc, res)
            if args.grafico:
                vis.graficar(esc, res)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
