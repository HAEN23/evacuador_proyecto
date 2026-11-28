"""Interfaz de línea de comandos."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import experimentos as exp
from . import experimentos_ag as exp_ag
from . import visualizacion as vis
from .generador import ConfigGenerador, generar_escenario
from .genetico import K_PERMITIDOS, ParametrosAG, optimizar
from .io_grupos import cargar_grupos
from .io_csv import cargar_csv, guardar_csv
from .ucs import buscar_ucs


def _parser() -> argparse.ArgumentParser:
    # La CLI organiza las operaciones como subcomandos.
    p = argparse.ArgumentParser(prog="evacuador",
                                description="Sistema de Evacuación Táctica: búsqueda de costo uniforme (UCS)")
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

    e = sub.add_parser("experimentos", help="corre UCS en varios escenarios y muestra la tabla")
    e.add_argument("--csv", metavar="ARCHIVO", help="guarda también la tabla en CSV")
    e.add_argument("--guardar-escenarios", metavar="CARPETA",
                   help="guarda cada escenario generado como CSV en esa carpeta")

    o = sub.add_parser("optimizar", help="ubica k salidas con el algoritmo genético (EvacuAG)")
    o.add_argument("escenario", help="CSV del escenario")
    o.add_argument("--grupos", required=True, help="CSV de grupos (fila,columna,tamano)")
    _opciones_ag(o, k=3)
    o.add_argument("--salida", metavar="CARPETA",
                   help="guarda historial.csv y top3.csv (y las figuras con --grafico)")
    o.add_argument("--grafico", action="store_true",
                   help="genera las figuras (requiere matplotlib y --salida)")

    x = sub.add_parser("experimentos-ag",
                       help="compara el AG contra salidas al azar y búsqueda exhaustiva (A-D)")
    _opciones_ag(x, k=2, semilla=False)
    x.add_argument("--semillas", type=int, default=10, help="número de semillas (0..N-1)")
    x.add_argument("--sin-exhaustivo", action="store_true",
                   help="omite la búsqueda exhaustiva (es la parte más lenta)")
    x.add_argument("--csv", metavar="ARCHIVO", help="guarda también la tabla en CSV")

    a = sub.add_parser("ajuste-ag",
                       help="prueba combinaciones de sigma y élites del AG en los escenarios A-D")
    a.add_argument("--k", type=int, nargs="+", default=[3], choices=K_PERMITIDOS,
                   help="números de salidas a probar (por defecto 3)")
    a.add_argument("--sigmas", type=float, nargs="+", default=list(exp_ag.SIGMAS_AJUSTE))
    a.add_argument("--elitismos", type=int, nargs="+", default=list(exp_ag.ELITISMOS_AJUSTE))
    a.add_argument("--semillas", type=int, default=10, help="cuántas semillas usar")
    a.add_argument("--desde", type=int, default=0,
                   help="primera semilla (por defecto 0); sirve para validar con otras")
    a.add_argument("--csv", metavar="ARCHIVO", help="guarda también la tabla en CSV")

    sub.add_parser("gui", help="abre la interfaz gráfica (requiere tkinter)")
    return p


def _opciones_ag(p: argparse.ArgumentParser, k: int, semilla: bool = True) -> None:
    """Opciones del AG compartidas por `optimizar` y `experimentos-ag`."""
    p.add_argument("--k", type=int, default=k, help="número de salidas (2, 3 o 4)")
    p.add_argument("--d-min", type=int, default=3, help="distancia Manhattan mínima entre salidas")
    p.add_argument("--poblacion", type=int, default=20)
    p.add_argument("--generaciones", type=int, default=100)
    p.add_argument("--p-evac", type=float, default=0.9,
                   help="fracción de personas para el tiempo T_p, en (0, 1]")
    p.add_argument("--ventana", type=int, default=5, help="segundos de la ventana de aglomeración")
    if semilla:
        p.add_argument("--semilla", type=int, default=None)


def _parametros(args: argparse.Namespace, semilla: int | None = None) -> ParametrosAG:
    return ParametrosAG(tam_poblacion=args.poblacion, generaciones=args.generaciones, k=args.k,
                        d_min=args.d_min, p_evac=args.p_evac, ventana=args.ventana,
                        semilla=semilla)


def _optimizar(args: argparse.Namespace) -> None:
    if args.grafico and not args.salida:
        raise ValueError("--grafico necesita --salida para guardar las figuras")
    esc = cargar_csv(args.escenario)
    grupos = cargar_grupos(args.grupos)
    resultado = optimizar(esc, grupos, _parametros(args, args.semilla))
    # Se muestran unas 10 filas del historial; el CSV lo guarda completo.
    cada = max(1, args.generaciones // 10)
    print(f"Mejor individuo por generación (cada {cada}):\n")
    print(exp_ag.historial_markdown(resultado, cada))
    print("\nTres mejores configuraciones:\n")
    print(exp_ag.top3_markdown(resultado))
    if args.salida:
        carpeta = Path(args.salida)
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / "historial.csv").write_text(exp_ag.historial_csv(resultado) + "\n",
                                               encoding="utf-8")
        (carpeta / "top3.csv").write_text(exp_ag.top3_csv(resultado) + "\n", encoding="utf-8")
        print(f"\nCSV guardados en {carpeta}/ (historial.csv, top3.csv)")
        if args.grafico:
            from . import visualizacion_ag  # perezoso: solo aquí se necesita matplotlib
            for ruta in visualizacion_ag.guardar_figuras(carpeta, esc, grupos, resultado):
                print(f"Figura guardada en {ruta}")


def _experimentos_ag(args: argparse.Namespace) -> None:
    if args.semillas < 1:
        raise ValueError("--semillas debe ser al menos 1")
    filas = exp_ag.comparar_todos(_parametros(args), range(args.semillas),
                                  exhaustivo=not args.sin_exhaustivo)
    print(exp_ag.tabla_markdown(filas))
    if args.csv:
        with open(args.csv, "w", encoding="utf-8") as f:
            f.write(exp_ag.tabla_csv(filas) + "\n")
        print(f"\nTabla guardada en {args.csv}")


def _ajuste_ag(args: argparse.Namespace) -> None:
    if args.semillas < 1:
        raise ValueError("--semillas debe ser al menos 1")
    filas = exp_ag.barrido_parametros(ks=args.k, sigmas=args.sigmas, elitismos=args.elitismos,
                                      semillas=range(args.desde, args.desde + args.semillas))
    print(exp_ag.ajuste_markdown(filas))
    if args.csv:
        with open(args.csv, "w", encoding="utf-8") as f:
            f.write(exp_ag.ajuste_csv(filas) + "\n")
        print(f"\nTabla guardada en {args.csv}")


def _gui() -> None:
    # Importación perezosa: los otros comandos no requieren tkinter ni matplotlib.
    try:
        from .gui.app import iniciar_interfaz
    except ImportError as exc:
        raise RuntimeError(
            f"No se pudo cargar la interfaz gráfica ({exc}). Instale tkinter y matplotlib: "
            "sudo apt install python3-tk && pip install -r requirements.txt") from exc
    iniciar_interfaz()


def _experimentos(args: argparse.Namespace) -> None:
    escenarios = exp.construir_escenarios()
    filas = exp.ejecutar_todos(escenarios)
    print(exp.tabla_markdown(filas))
    if args.csv:
        with open(args.csv, "w", encoding="utf-8") as f:
            f.write(exp.tabla_csv(filas) + "\n")
        print(f"\nTabla guardada en {args.csv}")
    if args.guardar_escenarios:
        carpeta = Path(args.guardar_escenarios)
        carpeta.mkdir(parents=True, exist_ok=True)
        for nombre, esc in escenarios:
            archivo = carpeta / (nombre.split(".")[0].lower() + "_" + exp.slug(nombre) + ".csv")
            guardar_csv(archivo, esc)
        print(f"Escenarios guardados en {carpeta}/")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.cmd == "generar":
            cfg = ConfigGenerador(args.filas, args.cols, args.densidad,
                                  args.focos, args.radio, args.seed)
            guardar_csv(args.salida, generar_escenario(cfg))
            print(f"Escenario guardado en {args.salida}")
        elif args.cmd == "experimentos":
            _experimentos(args)
        elif args.cmd == "optimizar":
            _optimizar(args)
        elif args.cmd == "experimentos-ag":
            _experimentos_ag(args)
        elif args.cmd == "ajuste-ag":
            _ajuste_ag(args)
        elif args.cmd == "gui":
            _gui()
        else:
            esc = cargar_csv(args.entrada)
            res = buscar_ucs(esc)
            if args.animar:
                vis.animar(esc, res, args.pausa)
            vis.mostrar_resultado(esc, res)
            if args.grafico:
                vis.graficar(esc, res)
    # Presenta errores esperables sin traceback y comunica el fallo con código 1.
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
