"""Pruebas de las rutas por grupo y de las figuras del AG (se saltan sin matplotlib)."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from evacuador import cli
from evacuador.genetico import Grupo, ParametrosAG, optimizar
from evacuador.modelos import Escenario
from evacuador.visualizacion_ag import dibujar_mapa_detallado, guardar_figuras, rutas_grupos

HAY_MATPLOTLIB = importlib.util.find_spec("matplotlib") is not None
DATA = Path(__file__).resolve().parent.parent / "data"
# Fila 0 libre, fila 1 muro, fila 2 humo: el grupo de abajo no puede llegar a ninguna salida.
ESC = Escenario.desde_listas([[1, 1, 1, 1, 1], [0, 0, 0, 0, 0], [5, 5, 5, 5, 5]],
                             (0, 0), [(0, 4)])


class TestRutas(unittest.TestCase):
    def test_rutas_a_mano(self):
        rutas = rutas_grupos(ESC, [(0, 1, 2), Grupo((2, 2), 1)], ((0, 0), (0, 4)))
        self.assertEqual(rutas[0], [(0, 1), (0, 0)])   # la salida más cercana
        self.assertIsNone(rutas[1])                    # aislado detrás del muro
        self.assertEqual(rutas_grupos(ESC, [(0, 1)], ()), [None])


@unittest.skipUnless(HAY_MATPLOTLIB, "matplotlib no está instalado")
class TestFiguras(unittest.TestCase):
    def test_guardar_figuras_con_grupo_sin_ruta(self):
        res = optimizar(ESC, [(0, 1, 2), (2, 2, 1)],
                        ParametrosAG(k=2, d_min=3, tam_poblacion=4, generaciones=3, semilla=1))
        with tempfile.TemporaryDirectory() as tmp:
            rutas = guardar_figuras(tmp, ESC, [(0, 1, 2), (2, 2, 1)], res)
            self.assertEqual([r.name for r in rutas],
                             ["evolucion_aptitud.png", "top3_mapa.png", "curva_evacuacion.png"])
            self.assertTrue(all(r.stat().st_size > 0 for r in rutas))

    def test_mapa_detallado_marca_cada_celda_y_cada_salida(self):
        from matplotlib.figure import Figure

        res = optimizar(ESC, [(0, 1, 2)],
                        ParametrosAG(k=2, d_min=3, tam_poblacion=4, generaciones=3, semilla=1))
        figura = Figure()
        dibujar_mapa_detallado(figura, ESC, [(0, 1, 2)], res.mejor, 1)
        ejes = figura.axes[0]
        self.assertEqual(list(ejes.get_xticks()), list(range(5)))
        self.assertEqual(len(ejes.texts), 2)   # una etiqueta por salida

    def test_cli_optimizar_con_salida_y_grafico(self):
        with tempfile.TemporaryDirectory() as tmp:
            codigo = cli.main(["optimizar", str(DATA / "a_sin_humo.csv"),
                               "--grupos", str(DATA / "grupos_a.csv"), "--k", "2",
                               "--generaciones", "3", "--semilla", "7",
                               "--salida", tmp, "--grafico"])
            self.assertEqual(codigo, 0)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()),
                             ["curva_evacuacion.png", "evolucion_aptitud.png",
                              "historial.csv", "top3.csv", "top3_mapa.png"])


if __name__ == "__main__":
    unittest.main()
