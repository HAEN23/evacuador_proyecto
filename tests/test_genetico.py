"""Pruebas del núcleo del algoritmo genético."""
import dataclasses
import math
import unittest

from evacuador.generador import ConfigGenerador, generar_escenario
from evacuador.genetico import (ParametrosAG, codificar, crear_problema, decodificar,
                                evaluar, optimizar, reparar)
from evacuador.modelos import Escenario

# Cuadrícula 3x3 libre: permite calcular a mano los riesgos esperados.
LIBRE_3X3 = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]


def _problema(grid, ocupantes, k=2, d_min=1, r_ref=1.0):
    """Problema con R_ref fijo para que las cuentas sean exactas."""
    esc = Escenario.desde_listas(grid, (0, 0), [(0, 0)])
    problema = crear_problema(esc, ocupantes, ParametrosAG(k=k, d_min=d_min))
    return dataclasses.replace(problema, r_ref=r_ref)


class TestCromosoma(unittest.TestCase):
    def test_extremos_se_decodifican_a_las_esquinas(self):
        self.assertEqual(decodificar([0.0, 0.0, 1.0, 1.0], 5, 8), [(0, 0), (4, 7)])

    def test_x_es_columna_e_y_es_fila(self):
        self.assertEqual(decodificar([1.0, 0.0], 5, 8), [(0, 7)])

    def test_codificar_es_inversa_de_decodificar(self):
        posiciones = [(2, 3), (0, 7), (4, 0)]
        genes = codificar(posiciones, 5, 8)
        self.assertEqual(decodificar(genes, 5, 8), posiciones)
        self.assertTrue(all(0.0 <= g <= 1.0 for g in genes))


class TestReparacion(unittest.TestCase):
    def setUp(self):
        # Muro en el centro y humo en la esquina inferior derecha.
        self.grid = [[1, 1, 1], [1, 0, 1], [1, 1, 5]]
        self.validas = tuple((f, c) for f in range(3) for c in range(3)
                             if self.grid[f][c] == 1)
        self.set = frozenset(self.validas)

    def test_salida_valida_no_se_mueve(self):
        self.assertEqual(reparar([(0, 0), (2, 0)], self.validas, self.set, 1),
                         [(0, 0), (2, 0)])

    def test_salida_en_muro_pasa_a_la_celda_valida_mas_cercana(self):
        # (1,1) es muro; sus vecinas válidas empatan y gana la menor fila-columna.
        self.assertEqual(reparar([(1, 1)], self.validas, self.set, 1), [(0, 1)])

    def test_salida_en_humo_se_mueve(self):
        self.assertEqual(reparar([(2, 2)], self.validas, self.set, 1), [(1, 2)])

    def test_respeta_distancia_minima_entre_salidas(self):
        res = reparar([(0, 0), (0, 1)], self.validas, self.set, 3)
        self.assertIsNotNone(res)
        self.assertGreaterEqual(abs(res[0][0] - res[1][0]) + abs(res[0][1] - res[1][1]), 3)

    def test_sin_lugar_devuelve_none(self):
        self.assertIsNone(reparar([(0, 0), (0, 1)], self.validas, self.set, 99))


class TestEvaluacion(unittest.TestCase):
    def test_valores_calculados_a_mano(self):
        # Cada ocupante tiene una salida adyacente: riesgo 1, carga 1-1.
        p = _problema(LIBRE_3X3, [(0, 0), (2, 2)])
        c = evaluar(p, ((0, 1), (2, 1)))
        self.assertEqual((c.o1, c.o2, c.o3, c.o4), (1.0, 1.0, 1.0, 0.0))
        self.assertAlmostEqual(c.aptitud, 1 / 4)
        self.assertEqual(c.ocupantes_por_salida, (1, 1))

    def test_desbalance_maximo_es_raiz_de_k_menos_1(self):
        # Los dos ocupantes van a la misma salida: O4 vale sqrt(k-1) = 1.
        p = _problema(LIBRE_3X3, [(0, 0), (1, 0)])
        c = evaluar(p, ((0, 1), (2, 2)))
        self.assertEqual(c.ocupantes_por_salida, (2, 0))
        self.assertAlmostEqual(c.o4, math.sqrt(2 - 1))

    def test_sin_ninguna_ruta_la_aptitud_es_cero_sin_dividir_por_cero(self):
        grid = [[1, 0, 1], [1, 0, 1], [1, 0, 1]]
        p = _problema(grid, [(1, 0)])
        c = evaluar(p, ((0, 2), (2, 2)))
        self.assertEqual((c.o1, c.o2, c.o3, c.o4, c.aptitud), (0.0, 0.0, 0.0, 0.0, 0.0))

    def test_cobertura_parcial(self):
        grid = [[1, 1, 0, 1], [1, 1, 0, 1], [1, 1, 0, 1]]
        p = _problema(grid, [(0, 0), (1, 3)])
        c = evaluar(p, ((2, 0), (1, 1)))   # ambas salidas del lado izquierdo
        self.assertEqual(c.o1, 0.5)
        self.assertGreater(c.aptitud, 0.0)

    def test_aptitud_siempre_en_cero_uno(self):
        p = _problema(LIBRE_3X3, [(0, 0), (1, 1), (2, 2)], r_ref=0.5)
        for salidas in (((0, 1), (2, 1)), ((0, 0), (2, 2)), ((1, 0), (1, 2))):
            self.assertTrue(0.0 <= evaluar(p, salidas).aptitud <= 1.0)


class TestProblema(unittest.TestCase):
    def test_ocupante_fuera_del_mapa(self):
        esc = Escenario.desde_listas(LIBRE_3X3, (0, 0), [(2, 2)])
        with self.assertRaises(ValueError):
            crear_problema(esc, [(9, 9)], ParametrosAG(k=2))

    def test_sin_ocupantes(self):
        esc = Escenario.desde_listas(LIBRE_3X3, (0, 0), [(2, 2)])
        with self.assertRaises(ValueError):
            crear_problema(esc, [], ParametrosAG(k=2))

    def test_r_ref_es_positivo_y_se_repite_igual(self):
        esc = Escenario.desde_listas(LIBRE_3X3, (0, 0), [(2, 2)])
        a = crear_problema(esc, [(0, 0), (2, 2)], ParametrosAG(k=2, d_min=1))
        b = crear_problema(esc, [(0, 0), (2, 2)], ParametrosAG(k=2, d_min=1))
        self.assertGreater(a.r_ref, 0)
        self.assertEqual(a.r_ref, b.r_ref)

    def test_parametros_invalidos(self):
        for malos in ({"k": 5}, {"tam_poblacion": 1}, {"elitismo": 20},
                      {"p_cruza": 1.5}, {"generaciones": 0}, {"d_min": 0}):
            with self.assertRaises(ValueError, msg=str(malos)):
                ParametrosAG(**malos)


class TestOptimizar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.esc = generar_escenario(ConfigGenerador(filas=10, columnas=14, seed=5))
        cls.ocupantes = [(0, 0), (0, 13), (9, 0), (5, 6), (3, 10)]
        # Si un ocupante cae en un muro simplemente no tiene ruta; no rompe nada.
        cls.params = ParametrosAG(tam_poblacion=10, generaciones=8, k=3, d_min=2, semilla=42)
        cls.resultado = optimizar(cls.esc, cls.ocupantes, cls.params)

    def test_misma_semilla_mismo_resultado(self):
        otra = optimizar(self.esc, self.ocupantes, self.params)
        self.assertEqual(otra, self.resultado)

    def test_historial_incluye_generacion_cero(self):
        self.assertEqual(len(self.resultado.historial), self.params.generaciones + 1)
        self.assertEqual([g.numero for g in self.resultado.historial],
                         list(range(self.params.generaciones + 1)))

    def test_elitismo_nunca_empeora_al_mejor(self):
        mejores = [g.aptitud_mejor for g in self.resultado.historial]
        self.assertEqual(mejores, sorted(mejores))

    def test_orden_de_promedio_mejor_peor(self):
        for g in self.resultado.historial:
            self.assertLessEqual(g.aptitud_peor, g.aptitud_promedio + 1e-12)
            self.assertLessEqual(g.aptitud_promedio, g.aptitud_mejor + 1e-12)

    def test_top3_distintas_y_ordenadas(self):
        top = self.resultado.top3
        self.assertTrue(1 <= len(top) <= 3)
        self.assertEqual(len({c.salidas for c in top}), len(top))
        self.assertEqual([c.aptitud for c in top], sorted((c.aptitud for c in top), reverse=True))
        self.assertEqual(self.resultado.mejor, top[0])

    def test_el_mejor_historico_coincide_con_el_top1(self):
        self.assertAlmostEqual(self.resultado.mejor.aptitud,
                               max(g.aptitud_mejor for g in self.resultado.historial))

    def test_las_salidas_cumplen_las_restricciones(self):
        for conf in self.resultado.top3:
            self.assertEqual(len(conf.salidas), self.params.k)
            for f, c in conf.salidas:
                self.assertEqual(self.esc.grid[f][c], 1)
            for i, a in enumerate(conf.salidas):
                for b in conf.salidas[i + 1:]:
                    self.assertGreaterEqual(abs(a[0] - b[0]) + abs(a[1] - b[1]),
                                            self.params.d_min)

    def test_cuenta_evaluaciones(self):
        self.assertGreaterEqual(self.resultado.evaluaciones, 1)


if __name__ == "__main__":
    unittest.main()
