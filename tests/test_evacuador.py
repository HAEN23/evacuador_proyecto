import tempfile
import unittest
from pathlib import Path

from evacuador import (ConfigGenerador, Escenario, buscar_ucs, cargar_csv,
                       generar_escenario, guardar_csv)


class TestUCS(unittest.TestCase):
    def test_prefiere_ruta_limpia_larga_sobre_atajo_con_humo(self):
        grid = [[1, 90, 1],
                [1, 0, 1],
                [1, 1, 1]]
        # Atajo por (0,1): 90+1+1+1 = 93. Rodeo limpio: 1+1+1+1 = 4
        res = buscar_ucs(Escenario.desde_listas(grid, (0, 0), [(2, 2)]))
        self.assertEqual(res.costo, 4)
        self.assertEqual(res.celdas_humo, 0)

    def test_sin_ruta(self):
        grid = [[1, 0, 1], [0, 0, 1], [1, 1, 1]]
        res = buscar_ucs(Escenario.desde_listas(grid, (0, 0), [(2, 2)]))
        self.assertFalse(res.encontrada)

    def test_inicio_bloqueado(self):
        res = buscar_ucs(Escenario.desde_listas([[0, 1], [1, 1]], (0, 0), [(1, 1)]))
        self.assertFalse(res.encontrada)

    def test_elige_la_salida_mas_barata(self):
        # Izquierda: 1 + 9 = 10. Derecha: 1 + 1 = 2.
        grid = [[9, 1, 1, 1, 1]]
        res = buscar_ucs(Escenario.desde_listas(grid, (0, 2), [(0, 0), (0, 4)]))
        self.assertEqual(res.ruta[-1], (0, 4))
        self.assertEqual(res.costo, 2)

    def test_inicio_igual_a_meta(self):
        res = buscar_ucs(Escenario.desde_listas([[1]], (0, 0), [(0, 0)]))
        self.assertEqual(res.costo, 0)


class TestEscenario(unittest.TestCase):
    def test_rechaza_valores_fuera_de_rango(self):
        with self.assertRaises(ValueError):
            Escenario.desde_listas([[1, 100]], (0, 0), [(0, 1)])

    def test_rechaza_posicion_fuera(self):
        with self.assertRaises(ValueError):
            Escenario.desde_listas([[1, 1]], (0, 0), [(5, 5)])


class TestGeneradorYCSV(unittest.TestCase):
    def test_semilla_reproducible(self):
        cfg = ConfigGenerador(10, 10, seed=3)
        self.assertEqual(generar_escenario(cfg), generar_escenario(cfg))

    def test_escenario_generado_es_resoluble(self):
        self.assertTrue(buscar_ucs(generar_escenario(ConfigGenerador(12, 12, seed=1))).encontrada)

    def test_ida_y_vuelta_csv(self):
        esc = generar_escenario(ConfigGenerador(8, 9, seed=5))
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "e.csv"
            guardar_csv(ruta, esc)
            self.assertEqual(cargar_csv(ruta), esc)


if __name__ == "__main__":
    unittest.main()
