import tempfile
import unittest
from pathlib import Path

from evacuador import experimentos as exp
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


class TestExperimentos(unittest.TestCase):
    def test_tabla_tiene_una_fila_por_escenario(self):
        filas = exp.ejecutar_todos()
        self.assertEqual(len(filas), len(exp.CONFIGURACIONES) + 1)
        self.assertEqual(len(exp.tabla_markdown(filas).splitlines()), len(filas) + 2)

    def test_resultados_son_reproducibles(self):
        a = [(f.costo, f.pasos, f.nodos_expandidos) for f in exp.ejecutar_todos()]
        b = [(f.costo, f.pasos, f.nodos_expandidos) for f in exp.ejecutar_todos()]
        self.assertEqual(a, b)

    def test_escenario_sin_humo_no_cruza_humo(self):
        fila = exp.ejecutar_todos()[0]
        self.assertEqual(fila.celdas_humo, 0)
        self.assertEqual(fila.costo, fila.pasos)  # todas las celdas cuestan 1

    def test_caso_sin_ruta_se_reporta(self):
        fila = exp.ejecutar("x", exp.escenario_sin_ruta())
        self.assertFalse(fila.encontrada)
        self.assertIn("sin ruta", exp.tabla_markdown([fila]))

    def test_umbral_de_humo_cuenta_cualquier_valor_desde_2(self):
        res = buscar_ucs(Escenario.desde_listas([[1, 2, 1]], (0, 0), [(0, 2)]))
        self.assertEqual(res.celdas_humo, 1)


if __name__ == "__main__":
    unittest.main()
