import unittest

try:
    import matplotlib
    matplotlib.use("Agg")
    from evacuador.visualizacion import dibujar_mapa, nueva_figura
    HAY_MATPLOTLIB = True
except ImportError:  # el núcleo funciona sin matplotlib
    HAY_MATPLOTLIB = False

from evacuador import Escenario, buscar_ucs


@unittest.skipUnless(HAY_MATPLOTLIB, "requiere matplotlib y numpy")
class TestDibujarMapa(unittest.TestCase):
    def _dibujar(self, grid, inicio, metas):
        esc = Escenario.desde_listas(grid, inicio, metas)
        res = buscar_ucs(esc)
        figura = nueva_figura()
        ejes = figura.add_subplot(111)
        dibujar_mapa(figura, ejes, esc, res)
        figura.canvas.draw()
        return ejes, res

    def test_con_ruta_dibuja_titulo_y_leyenda(self):
        ejes, res = self._dibujar([[1, 5, 1], [1, 0, 1], [1, 1, 1]], (0, 0), [(2, 2)])
        self.assertTrue(res.encontrada)
        self.assertIn("menor riesgo", ejes.get_title())
        etiquetas = [t.get_text() for t in ejes.figure.legends[0].get_texts()]
        self.assertIn("Ruta óptima de escape", etiquetas)
        self.assertIn("Punto de inicio", etiquetas)
        self.assertIn("Salida de emergencia", etiquetas)

    def test_sin_ruta_muestra_situacion_critica(self):
        ejes, res = self._dibujar([[1, 0, 1], [0, 0, 1], [1, 1, 1]], (0, 0), [(2, 2)])
        self.assertFalse(res.encontrada)
        self.assertIn("Situación crítica", ejes.get_title())
        etiquetas = [t.get_text() for t in ejes.figure.legends[0].get_texts()]
        self.assertNotIn("Ruta óptima de escape", etiquetas)

    def test_varias_salidas_se_etiquetan_una_vez(self):
        ejes, _ = self._dibujar([[1, 1, 1], [1, 1, 1], [1, 1, 1]], (1, 1), [(0, 0), (2, 2)])
        etiquetas = [t.get_text() for t in ejes.figure.legends[0].get_texts()]
        self.assertEqual(etiquetas.count("Salida de emergencia"), 1)


if __name__ == "__main__":
    unittest.main()
