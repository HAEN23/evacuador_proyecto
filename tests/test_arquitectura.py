"""Hace cumplir las reglas del README: las dependencias apuntan al núcleo."""
import ast
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent / "evacuador"
NUCLEO = {"config", "modelos", "ucs", "generador", "io_csv", "experimentos",
          "visualizacion", "edicion", "cli"}
CAPAS_NUCLEO = {"config", "modelos", "ucs", "generador", "io_csv", "edicion"}


def _importa(ruta: Path) -> set[str]:
    """Nombres de módulos importados (incluye los relativos, sin el punto)."""
    nombres = set()
    for nodo in ast.walk(ast.parse(ruta.read_text(encoding="utf-8"))):
        if isinstance(nodo, ast.Import):
            nombres |= {a.name for a in nodo.names}
        elif isinstance(nodo, ast.ImportFrom):
            base = nodo.module or ""
            if nodo.level:
                nombres.add(("." * nodo.level) + base)
                nombres |= {("." * nodo.level) + base + "." + a.name for a in nodo.names}
            else:
                nombres.add(base)
    return nombres


def _top(nombre: str) -> str:
    return nombre.lstrip(".").split(".")[0]


class TestArquitectura(unittest.TestCase):
    def test_el_nucleo_no_importa_tkinter_ni_la_interfaz(self):
        for modulo in NUCLEO - {"cli"}:
            importados = {_top(n) for n in _importa(RAIZ / f"{modulo}.py")}
            self.assertNotIn("tkinter", importados, modulo)
            self.assertNotIn("gui", importados, modulo)

    def test_el_dominio_no_depende_de_servicios_ni_presentacion(self):
        permitidos = {"config", "modelos"}
        for modulo in ("ucs", "modelos", "config"):
            propios = {_top(n) for n in _importa(RAIZ / f"{modulo}.py")
                       if n.startswith(".")}
            self.assertLessEqual(propios - {""}, permitidos, modulo)

    def test_matplotlib_solo_se_importa_dentro_de_funciones(self):
        arbol = ast.parse((RAIZ / "visualizacion.py").read_text(encoding="utf-8"))
        for nodo in arbol.body:
            if isinstance(nodo, (ast.Import, ast.ImportFrom)):
                nombre = getattr(nodo, "module", None) or nodo.names[0].name
                self.assertFalse(nombre.startswith(("matplotlib", "numpy")), nombre)

    def test_vistas_de_la_gui_no_se_importan_entre_si(self):
        # Solo app.py conoce a editor y resultado; estas dependen de tema, no de app.
        for modulo in ("editor", "resultado", "tema"):
            propios = {_top(n) for n in _importa(RAIZ / "gui" / f"{modulo}.py")}
            self.assertNotIn("app", propios, modulo)
        self.assertNotIn("resultado", {_top(n) for n in _importa(RAIZ / "gui" / "editor.py")})
        self.assertNotIn("editor", {_top(n) for n in _importa(RAIZ / "gui" / "resultado.py")})
        self.assertNotIn("editor", {_top(n) for n in _importa(RAIZ / "gui" / "tema.py")})

    def test_el_nucleo_no_usa_print_salvo_cli_y_visualizacion(self):
        for ruta in RAIZ.glob("*.py"):
            if ruta.stem in {"cli", "visualizacion", "__main__"}:
                continue
            for nodo in ast.walk(ast.parse(ruta.read_text(encoding="utf-8"))):
                if isinstance(nodo, ast.Call) and getattr(nodo.func, "id", "") in {"print", "input"}:
                    self.fail(f"{ruta.name}: print/input fuera de cli y visualizacion")

    def test_sin_estado_global_en_la_gui(self):
        for ruta in (RAIZ / "gui").glob("*.py"):
            for nodo in ast.walk(ast.parse(ruta.read_text(encoding="utf-8"))):
                self.assertNotIsInstance(nodo, ast.Global, ruta.name)


if __name__ == "__main__":
    unittest.main()
