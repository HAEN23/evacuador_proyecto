"""Pruebas de las explicaciones del panel izquierdo de resultados (se saltan sin tkinter)."""
import importlib.util
import unittest
from dataclasses import replace

from evacuador.genetico import ParametrosAG, optimizar
from evacuador.modelos import Escenario

HAY_TK = importlib.util.find_spec("tkinter") is not None
ESC = Escenario.desde_listas([[1, 1, 1, 1, 1], [1, 5, 5, 5, 1], [1, 1, 1, 1, 1]],
                             (0, 0), [(0, 4)])


@unittest.skipUnless(HAY_TK, "tkinter no está instalado")
class TestTextos(unittest.TestCase):
    def setUp(self):
        self.res = optimizar(ESC, [(1, 0, 3), (2, 2, 2)],
                             ParametrosAG(k=2, d_min=2, tam_poblacion=6, generaciones=4,
                                          semilla=1))

    def test_mapa_usa_los_datos_de_cada_configuracion(self):
        from evacuador.gui.resultado_ag import texto_mapa

        mejor = self.res.top3[0]
        segunda = replace(self.res.top3[1], aptitud=mejor.aptitud - 0.01)
        texto = texto_mapa(segunda, 2, mejor, 5, 5)
        self.assertIn("segunda mejor", texto)
        self.assertIn("de las 5 personas", texto)
        for (f, c), n in zip(segunda.salidas, segunda.personas_por_salida):
            self.assertIn(f"({f}, {c}): llegan {n} personas", texto)
        self.assertIn("0.0100 menor que la del mapa #1", texto)
        self.assertIn("prácticamente igual", texto_mapa(mejor, 2, mejor, 5, 5))
        self.assertNotIn("mapa #1.", texto_mapa(mejor, 1, mejor, 5, 5))

    def test_comparacion_dice_quien_gana(self):
        from evacuador.gui.resultado_ag import texto_comparacion

        mejor = self.res.top3[0]
        peor = replace(mejor, aptitud=mejor.aptitud / 2)
        self.assertIn("algoritmo son mejores", texto_comparacion(mejor, peor))
        self.assertIn("mejor aptitud que las del algoritmo", texto_comparacion(peor, mejor))
        self.assertIn("empatan", texto_comparacion(mejor, mejor))

    def test_evolucion_y_curvas(self):
        from evacuador.gui.resultado_ag import texto_curvas, texto_evolucion

        self.assertIn("generación", texto_evolucion(self.res))
        self.assertIn(f"#1: el 90 % sale en {self.res.top3[0].t90} s", texto_curvas(self.res))
