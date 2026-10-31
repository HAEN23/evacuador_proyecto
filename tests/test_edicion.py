import unittest

from evacuador.config import BLOQUEADA, COSTO_MIN, DIMENSION_MAX, DIMENSION_MIN
from evacuador.edicion import (DisenoEscenario, DisenoInvalido, Herramienta,
                               limitar_dimension)
from evacuador import Escenario, buscar_ucs


class TestDisenoEscenario(unittest.TestCase):
    def setUp(self):
        self.d = DisenoEscenario(5, 6)

    def test_nueva_cuadricula_esquinas_opuestas(self):
        self.assertEqual((self.d.filas, self.d.columnas), (5, 6))
        self.assertEqual(self.d.inicio, (0, 0))
        self.assertEqual(self.d.salidas, [(4, 5)])
        self.assertTrue(all(v == COSTO_MIN for fila in self.d.grid for v in fila))

    def test_dimensiones_se_limitan(self):
        self.assertEqual(limitar_dimension(1), DIMENSION_MIN)
        self.assertEqual(limitar_dimension(999), DIMENSION_MAX)
        self.assertEqual(DisenoEscenario(1, 999).columnas, DIMENSION_MAX)

    def test_pared_y_humo(self):
        self.d.aplicar(Herramienta.BLOQUEADA, (1, 1))
        self.d.aplicar("humo", (2, 2), nivel_humo=40)
        self.assertEqual(self.d.valor((1, 1)), BLOQUEADA)
        self.assertEqual(self.d.valor((2, 2)), 40)

    def test_pared_quita_inicio_y_salida(self):
        self.d.aplicar(Herramienta.BLOQUEADA, (0, 0))
        self.d.aplicar(Herramienta.BLOQUEADA, (4, 5))
        self.assertIsNone(self.d.inicio)
        self.assertEqual(self.d.salidas, [])

    def test_inicio_y_salida_son_unicos_y_se_trasladan(self):
        self.d.aplicar(Herramienta.INICIO, (2, 2))
        self.d.aplicar(Herramienta.SALIDA, (3, 3))
        self.assertEqual(self.d.inicio, (2, 2))
        self.assertEqual(self.d.salidas, [(3, 3)])

    def test_colocar_salida_sobre_inicio_lo_quita(self):
        self.d.aplicar(Herramienta.SALIDA, (0, 0))
        self.assertIsNone(self.d.inicio)
        self.assertEqual(self.d.salidas, [(0, 0)])

    def test_colocar_inicio_sobre_pared_la_libera(self):
        self.d.aplicar(Herramienta.BLOQUEADA, (2, 2))
        self.d.aplicar(Herramienta.INICIO, (2, 2))
        self.assertEqual(self.d.valor((2, 2)), COSTO_MIN)
        self.assertEqual(self.d.inicio, (2, 2))

    def test_borrar_restaura_la_celda(self):
        self.d.aplicar(Herramienta.HUMO, (1, 1), 70)
        self.d.aplicar(Herramienta.BORRAR, (1, 1))
        self.assertEqual(self.d.valor((1, 1)), COSTO_MIN)
        self.d.aplicar(Herramienta.BORRAR, (0, 0))
        self.assertIsNone(self.d.inicio)

    def test_libre_marca_y_otras_herramientas_desmarcan(self):
        self.d.aplicar(Herramienta.LIBRE, (1, 1))
        self.assertIn((1, 1), self.d.libres_marcadas)
        self.d.aplicar(Herramienta.HUMO, (1, 1), 30)
        self.assertNotIn((1, 1), self.d.libres_marcadas)

    def test_posicion_fuera_se_ignora(self):
        self.d.aplicar(Herramienta.BLOQUEADA, (99, 99))
        self.d.aplicar(Herramienta.BLOQUEADA, (-1, 0))

    def test_restaurar_conserva_inicio_y_salida(self):
        self.d.aplicar(Herramienta.BLOQUEADA, (1, 1))
        self.d.restaurar()
        self.assertEqual(self.d.valor((1, 1)), COSTO_MIN)
        self.assertEqual(self.d.inicio, (0, 0))
        self.assertEqual(self.d.salidas, [(4, 5)])

    def test_a_escenario_y_resolucion(self):
        esc = self.d.a_escenario()
        self.assertIsInstance(esc, Escenario)
        self.assertTrue(buscar_ucs(esc).encontrada)

    def test_a_escenario_sin_inicio_o_salida(self):
        self.d.aplicar(Herramienta.BORRAR, (0, 0))
        with self.assertRaises(DisenoInvalido) as ctx:
            self.d.a_escenario()
        self.assertEqual(ctx.exception.titulo, "Escenario incompleto")
        self.d.aplicar(Herramienta.INICIO, (0, 0))
        self.d.aplicar(Herramienta.BORRAR, (4, 5))
        with self.assertRaises(DisenoInvalido):
            self.d.a_escenario()

    def test_cargar_escenario_existente(self):
        esc = Escenario.desde_listas([[1, 0], [1, 1]], (0, 0), [(1, 1)])
        self.d.cargar(esc)
        self.assertEqual((self.d.filas, self.d.columnas), (2, 2))
        self.assertEqual(self.d.a_escenario(), esc)

    def test_diseno_sin_pared_en_ruta_cierra_el_paso(self):
        for f in range(5):
            self.d.aplicar(Herramienta.BLOQUEADA, (f, 3))
        self.assertFalse(buscar_ucs(self.d.a_escenario()).encontrada)


if __name__ == "__main__":
    unittest.main()
