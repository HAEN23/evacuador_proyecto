"""Pruebas de la lógica del editor del AG (sin tkinter)."""
import unittest

from evacuador.config import BLOQUEADA
from evacuador.edicion import DisenoInvalido, Herramienta
from evacuador.edicion_ag import DisenoAG
from evacuador.genetico import Grupo
from evacuador.modelos import Escenario


class TestDisenoAG(unittest.TestCase):
    def setUp(self):
        self.d = DisenoAG(4, 5)

    def test_colocar_y_redimensionar_grupo(self):
        self.d.aplicar(Herramienta.GRUPO, (1, 1), tamano=3)
        self.d.aplicar("grupo", (1, 1), tamano=7)      # mismo lugar: cambia el tamaño
        self.d.aplicar(Herramienta.GRUPO, (2, 3), tamano=0)  # se ajusta a 1
        self.assertEqual(self.d.lista_grupos(), [Grupo((1, 1), 7), Grupo((2, 3), 1)])
        self.assertEqual(self.d.personas, 8)

    def test_grupo_despeja_muro_y_muro_quita_grupo(self):
        self.d.aplicar(Herramienta.BLOQUEADA, (0, 2))
        self.d.aplicar(Herramienta.GRUPO, (0, 2), tamano=2)
        self.assertNotEqual(self.d.valor((0, 2)), BLOQUEADA)
        self.d.aplicar(Herramienta.BLOQUEADA, (0, 2))
        self.assertEqual(self.d.grupos, {})

    def test_humo_conserva_grupo_y_borrar_lo_quita(self):
        self.d.aplicar(Herramienta.GRUPO, (3, 0), tamano=2)
        self.d.aplicar(Herramienta.HUMO, (3, 0), nivel_humo=40)
        self.assertEqual((self.d.valor((3, 0)), self.d.grupos), (40, {(3, 0): 2}))
        self.d.aplicar(Herramienta.BORRAR, (3, 0))
        self.assertEqual(self.d.grupos, {})

    def test_nueva_borra_grupos_y_cargar_conserva_los_validos(self):
        self.d.poner_grupos([Grupo((0, 0), 2), Grupo((3, 4), 5)])
        esc = Escenario.desde_listas([[1, 1, 1], [1, 0, 1]], (0, 0), [(1, 2)])
        self.d.cargar(esc)                       # (3, 4) queda fuera del nuevo mapa
        self.assertEqual(self.d.grupos, {(0, 0): 2})
        self.d.nueva(3, 3)
        self.assertEqual(self.d.grupos, {})

    def test_restaurar_quita_grupos_y_paredes(self):
        self.d.aplicar(Herramienta.BLOQUEADA, (1, 1))
        self.d.aplicar(Herramienta.GRUPO, (2, 2), tamano=3)
        self.d.restaurar()
        self.assertEqual(self.d.grupos, {})
        self.assertNotEqual(self.d.valor((1, 1)), BLOQUEADA)

    def test_poner_grupos_valida(self):
        self.d.aplicar(Herramienta.BLOQUEADA, (1, 1))
        with self.assertRaisesRegex(ValueError, "fuera"):
            self.d.poner_grupos([Grupo((9, 9))])
        with self.assertRaisesRegex(ValueError, "bloqueada"):
            self.d.poner_grupos([Grupo((1, 1))])
        # Dos grupos en la misma celda se suman.
        self.d.poner_grupos([Grupo((0, 0), 2), Grupo((0, 0), 3)])
        self.assertEqual(self.d.grupos, {(0, 0): 5})

    def test_a_escenario_completa_inicio_y_salida(self):
        self.d.aplicar(Herramienta.BLOQUEADA, (0, 0))   # quita el inicio
        self.d.aplicar(Herramienta.BLOQUEADA, (3, 4))   # quita la salida
        esc = self.d.a_escenario()
        self.assertEqual((esc.inicio, esc.metas), ((0, 1), ((3, 3),)))

    def test_todo_bloqueado(self):
        for f in range(4):
            for c in range(5):
                self.d.aplicar(Herramienta.BLOQUEADA, (f, c))
        with self.assertRaises(DisenoInvalido):
            self.d.a_escenario()


if __name__ == "__main__":
    unittest.main()
