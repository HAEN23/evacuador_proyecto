"""Pruebas de lectura, escritura y generación de grupos."""
import tempfile
import unittest
from pathlib import Path

from evacuador.genetico import Grupo
from evacuador.io_grupos import cargar_grupos, generar_grupos, guardar_grupos
from evacuador.modelos import Escenario

DATA = Path(__file__).resolve().parent.parent / "data"


class TestIoGrupos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _archivo(self, texto: str) -> Path:
        ruta = self.dir / "g.csv"
        ruta.write_text(texto, encoding="utf-8")
        return ruta

    def test_ida_y_vuelta(self):
        grupos = [Grupo((0, 1), 3), Grupo((4, 2), 1)]
        ruta = self.dir / "g.csv"
        guardar_grupos(ruta, grupos)
        self.assertEqual(ruta.read_text(encoding="utf-8").splitlines()[0], "fila,columna,tamano")
        self.assertEqual(cargar_grupos(ruta), grupos)

    def test_tolera_espacios_y_lineas_finales(self):
        ruta = self._archivo("fila, columna, tamano\n 2 , 3 , 5\n\n\n")
        self.assertEqual(cargar_grupos(ruta), [Grupo((2, 3), 5)])

    def test_errores_de_formato(self):
        casos = {
            "1,2,3\n": "encabezado",
            "": "encabezado",
            "fila,columna,tamano\n": "no tiene grupos",
            "fila,columna,tamano\n1,a,2\n": "no entero",
            "fila,columna,tamano\n1,2,0\n": "al menos 1",
            "fila,columna,tamano\n1,2,3\n\n4,5,6\n": "fila vacía",
            "fila,columna,tamano\n1,2\n": "3 valores",
            "fila,columna,tamano\n-1,2,3\n": "negativas",
        }
        for texto, mensaje in casos.items():
            with self.subTest(texto=texto):
                with self.assertRaisesRegex(ValueError, mensaje):
                    cargar_grupos(self._archivo(texto))

    def test_generar_es_reproducible_y_evita_muros(self):
        esc = Escenario.desde_listas([[1, 0, 1], [0, 5, 0], [1, 0, 1]], (0, 0), [(2, 2)])
        a = generar_grupos(esc, n=5, tamano_max=4, semilla=3)
        self.assertEqual(a, generar_grupos(esc, n=5, tamano_max=4, semilla=3))
        # Las 5 celdas transitables quedan ocupadas, cada una una sola vez.
        self.assertEqual({g.celda for g in a}, {(0, 0), (0, 2), (1, 1), (2, 0), (2, 2)})
        self.assertTrue(all(1 <= g.tamano <= 4 for g in a))

    def test_generar_valida_parametros(self):
        esc = Escenario.desde_listas([[1, 0], [0, 1]], (0, 0), [(1, 1)])
        for kwargs in ({"n": 3}, {"n": 0}, {"n": 1, "tamano_max": 0}):
            with self.subTest(**kwargs), self.assertRaises(ValueError):
                generar_grupos(esc, **kwargs)

    def test_archivos_de_datos(self):
        for letra in "abcd":
            with self.subTest(letra=letra):
                self.assertEqual(len(cargar_grupos(DATA / f"grupos_{letra}.csv")), 12)


if __name__ == "__main__":
    unittest.main()
