"""Pruebas del núcleo del algoritmo genético."""
import dataclasses
import unittest

from evacuador.generador import ConfigGenerador, generar_escenario
from evacuador.genetico import (Grupo, ParametrosAG, codificar, crear_problema, decodificar,
                                evaluar, optimizar, reparar)
from evacuador.genetico import _elegir_top3, _parecidas
from evacuador.modelos import Escenario

# Cuadrícula 3x3 libre: permite calcular a mano los riesgos y tiempos esperados.
LIBRE_3X3 = [[1, 1, 1], [1, 1, 1], [1, 1, 1]]


def _problema(grid, grupos, k=2, d_min=1, p_evac=0.9, ventana=5, r_ref=1.0, t_ref=1.0):
    """Problema con R_ref y T_ref fijos para que las cuentas sean exactas."""
    esc = Escenario.desde_listas(grid, (0, 0), [(0, 0)])
    problema = crear_problema(esc, grupos, ParametrosAG(k=k, d_min=d_min, p_evac=p_evac,
                                                        ventana=ventana))
    return dataclasses.replace(problema, r_ref=r_ref, t_ref=t_ref)


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
        # Cada grupo tiene una salida adyacente: 1 paso (1 s) y riesgo 1.
        p = _problema(LIBRE_3X3, [(0, 0), (2, 2)])
        c = evaluar(p, ((0, 1), (2, 1)))
        self.assertEqual((c.o1, c.o2, c.o3), (1.0, 1.0, 1.0))
        self.assertEqual(c.o4, 0.5)            # pico de 1 persona entre 2 que salen
        self.assertAlmostEqual(c.aptitud, 1 / 6)
        self.assertEqual(c.personas_por_salida, (1, 1))
        self.assertEqual((c.t50, c.t90, c.t100), (1, 1, 1))
        self.assertEqual(c.curva_evacuacion, ((1, 1.0),))

    def test_el_tiempo_es_un_segundo_por_casilla(self):
        # (1,0) llega a (0,1) en 2 pasos: dos casillas recorridas, 2 s y riesgo 2.
        p = _problema(LIBRE_3X3, [(1, 0)])
        c = evaluar(p, ((0, 1), (2, 2)))
        self.assertEqual(c.t100, 2)
        self.assertEqual(c.riesgo_promedio, 2.0)

    def test_tiempos_por_porcentaje(self):
        # Grupos a 1 s y a 2 s de la misma salida: T50 = 1, T90 = T100 = 2.
        p = _problema(LIBRE_3X3, [(0, 0), (1, 0)], ventana=5)
        c = evaluar(p, ((0, 1), (2, 2)))
        self.assertEqual((c.t50, c.t90, c.t100), (1, 2, 2))
        self.assertEqual(c.curva_evacuacion, ((1, 0.5), (2, 1.0)))
        self.assertEqual(c.o3, 2.0)            # p_evac = 0.9 -> T_p = 2, T_ref = 1

    def test_p_evac_cambia_el_tiempo_optimizado(self):
        p = _problema(LIBRE_3X3, [(0, 0), (1, 0)], p_evac=0.5)
        self.assertEqual(evaluar(p, ((0, 1), (2, 2))).o3, 1.0)   # T50 = 1

    def test_aglomeracion_depende_de_la_ventana(self):
        # Dos grupos llegan a la misma salida a 1 s y a 2 s.
        grupos = [(0, 0), (1, 0)]
        ancha = evaluar(_problema(LIBRE_3X3, grupos, ventana=5), ((0, 1), (2, 2)))
        estrecha = evaluar(_problema(LIBRE_3X3, grupos, ventana=1), ((0, 1), (2, 2)))
        self.assertEqual(ancha.aglomeracion_max, 2)
        self.assertEqual(ancha.o4, 1.0)
        self.assertEqual(estrecha.aglomeracion_max, 1)
        self.assertEqual(estrecha.o4, 0.5)

    def test_el_tamano_del_grupo_pesa(self):
        # Grupo de 3 personas a una salida y de 1 a la otra: peor ventana = 3 de 4.
        p = _problema(LIBRE_3X3, [(0, 0, 3), (2, 2, 1)])
        c = evaluar(p, ((0, 1), (2, 1)))
        self.assertEqual(c.personas_por_salida, (3, 1))
        self.assertEqual(c.aglomeracion_max, 3)
        self.assertEqual(c.o4, 0.75)
        self.assertEqual(c.curva_evacuacion, ((1, 1.0),))

    def test_cobertura_pondera_por_personas(self):
        # Grupo de 3 aislado por un muro y grupo de 1 con ruta: sale 1 de 4 personas.
        grid = [[1, 0, 1], [1, 0, 1], [1, 0, 1]]
        p = _problema(grid, [(0, 0, 3), (0, 2, 1)])
        c = evaluar(p, ((1, 2), (2, 2)))
        self.assertEqual(c.o1, 0.25)
        self.assertEqual(c.curva_evacuacion[-1][1], 0.25)

    def test_sin_ninguna_ruta_la_aptitud_es_cero_sin_dividir_por_cero(self):
        grid = [[1, 0, 1], [1, 0, 1], [1, 0, 1]]
        p = _problema(grid, [(1, 0)])
        c = evaluar(p, ((0, 2), (2, 2)))
        self.assertEqual((c.o1, c.o2, c.o3, c.o4, c.aptitud), (0.0, 0.0, 0.0, 0.0, 0.0))
        self.assertEqual((c.t50, c.t90, c.t100), (0, 0, 0))

    def test_tiempos_ordenados(self):
        p = _problema(LIBRE_3X3, [(0, 0), (1, 0), (2, 0), (2, 2)])
        c = evaluar(p, ((0, 1), (2, 1)))
        self.assertLessEqual(c.t50, c.t90)
        self.assertLessEqual(c.t90, c.t100)

    def test_aptitud_siempre_en_cero_uno(self):
        p = _problema(LIBRE_3X3, [(0, 0, 2), (1, 1), (2, 2, 3)], r_ref=0.5, t_ref=0.5)
        for salidas in (((0, 1), (2, 1)), ((0, 0), (2, 2)), ((1, 0), (1, 2))):
            self.assertTrue(0.0 <= evaluar(p, salidas).aptitud <= 1.0)


class TestProblema(unittest.TestCase):
    def test_grupo_fuera_del_mapa(self):
        esc = Escenario.desde_listas(LIBRE_3X3, (0, 0), [(2, 2)])
        with self.assertRaises(ValueError):
            crear_problema(esc, [(9, 9)], ParametrosAG(k=2))

    def test_sin_grupos(self):
        esc = Escenario.desde_listas(LIBRE_3X3, (0, 0), [(2, 2)])
        with self.assertRaises(ValueError):
            crear_problema(esc, [], ParametrosAG(k=2))

    def test_tamano_de_grupo_invalido(self):
        with self.assertRaises(ValueError):
            Grupo((0, 0), 0)

    def test_acepta_tuplas_y_objetos_grupo(self):
        esc = Escenario.desde_listas(LIBRE_3X3, (0, 0), [(2, 2)])
        p = crear_problema(esc, [(0, 0), (1, 1, 4), Grupo((2, 2), 2)], ParametrosAG(k=2, d_min=1))
        self.assertEqual([g.tamano for g in p.grupos], [1, 4, 2])

    def test_referencias_positivas_y_repetibles(self):
        esc = Escenario.desde_listas(LIBRE_3X3, (0, 0), [(2, 2)])
        a = crear_problema(esc, [(0, 0), (2, 2)], ParametrosAG(k=2, d_min=1))
        b = crear_problema(esc, [(0, 0), (2, 2)], ParametrosAG(k=2, d_min=1))
        self.assertGreater(a.r_ref, 0)
        self.assertGreater(a.t_ref, 0)
        self.assertEqual((a.r_ref, a.t_ref), (b.r_ref, b.t_ref))

    def test_parametros_invalidos(self):
        for malos in ({"k": 5}, {"tam_poblacion": 1}, {"elitismo": 20},
                      {"p_cruza": 1.5}, {"generaciones": 0}, {"d_min": 0},
                      {"p_evac": 0.0}, {"p_evac": 1.2}, {"ventana": 0}):
            with self.assertRaises(ValueError, msg=str(malos)):
                ParametrosAG(**malos)


class TestOptimizar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.esc = generar_escenario(ConfigGenerador(filas=10, columnas=14, seed=5))
        cls.grupos = [(0, 0, 4), (0, 13, 2), (9, 0, 3), (5, 6, 1), (3, 10, 5)]
        # Si un grupo cae en un muro simplemente no tiene ruta; no rompe nada.
        cls.params = ParametrosAG(tam_poblacion=10, generaciones=8, k=3, d_min=2, semilla=42)
        cls.resultado = optimizar(cls.esc, cls.grupos, cls.params)

    def test_misma_semilla_mismo_resultado(self):
        otra = optimizar(self.esc, self.grupos, self.params)
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

    def test_top3_respeta_la_separacion_minima(self):
        top = self.resultado.top3
        sep = self.params.separacion_top3
        for i, a in enumerate(top):
            for b in top[i + 1:]:
                self.assertFalse(_parecidas(a.salidas, b.salidas, sep))

    def test_sin_filtro_basta_con_que_sean_distintas(self):
        params = dataclasses.replace(self.params, separacion_top3=0)
        top = optimizar(self.esc, self.grupos, params).top3
        self.assertEqual(len({c.salidas for c in top}), len(top))

    def test_separacion_negativa_se_rechaza(self):
        with self.assertRaises(ValueError):
            ParametrosAG(separacion_top3=-1)

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

    def test_las_metricas_del_mejor_son_coherentes(self):
        m = self.resultado.mejor
        self.assertTrue(0.0 <= m.o1 <= 1.0)
        self.assertTrue(0.0 <= m.o4 <= 1.0)
        self.assertLessEqual(m.t50, m.t90)
        self.assertLessEqual(m.t90, m.t100)
        self.assertAlmostEqual(m.curva_evacuacion[-1][1], m.o1)
        self.assertEqual(sum(m.personas_por_salida), round(m.o1 * 15))

    def test_cuenta_evaluaciones(self):
        self.assertGreaterEqual(self.resultado.evaluaciones, 1)


if __name__ == "__main__":
    unittest.main()


class TestSeparacionTop3(unittest.TestCase):
    def test_parecidas_si_cada_salida_esta_cerca_de_alguna(self):
        a = ((0, 0), (5, 5))
        self.assertTrue(_parecidas(a, ((0, 1), (5, 4)), 1))
        self.assertFalse(_parecidas(a, ((0, 1), (5, 4)), 0))
        self.assertFalse(_parecidas(a, ((0, 1), (9, 9)), 1))

    def test_se_salta_la_que_se_parece_a_una_elegida(self):
        class C:  # solo importan las salidas
            def __init__(self, salidas):
                self.salidas = salidas
        c1, c2, c3 = C(((0, 0), (9, 9))), C(((0, 1), (9, 9))), C(((5, 5), (9, 9)))
        self.assertEqual(_elegir_top3([c1, c2, c3], 2), [c1, c3])
        self.assertEqual(_elegir_top3([c1, c2, c3], 0), [c1, c2, c3])
