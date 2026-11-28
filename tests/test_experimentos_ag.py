"""Pruebas de las líneas base (azar, exhaustiva) y de las tablas del AG."""
import contextlib
import csv
import io
import tempfile
import unittest
from pathlib import Path

from evacuador import cli
from evacuador import experimentos_ag as x
from evacuador.genetico import ParametrosAG, crear_problema, optimizar
from evacuador.modelos import Escenario

# Pasillo 1x7 con un grupo de 1 persona en el centro.
PASILLO = Escenario.desde_listas([[1] * 7], (0, 0), [(0, 6)])
GRUPO_CENTRO = [(0, 3, 1)]
PARAMS = ParametrosAG(k=2, d_min=3, tam_poblacion=6, generaciones=5, semilla=1)


class TestLineasBase(unittest.TestCase):
    def setUp(self):
        self.problema = crear_problema(PASILLO, GRUPO_CENTRO, PARAMS)

    def test_exhaustiva_caso_a_mano(self):
        # Con una salida en (0,3) el grupo sale en 0 s y sin riesgo: O1 = 1, O2 = O3 = 0
        # y O4 = 1/1 = 1, así que la aptitud es 1 · 1 · 1 · 1/2 = 0.5 (el máximo posible).
        mejor = x.busqueda_exhaustiva(self.problema)
        self.assertIn((0, 3), mejor.salidas)
        self.assertAlmostEqual(mejor.aptitud, 0.5)

    def test_exhaustiva_rechaza_problemas_grandes(self):
        self.assertEqual(x.combinaciones_exhaustivas(self.problema), 21)  # C(7, 2)
        with self.assertRaisesRegex(ValueError, "demasiado grande"):
            x.busqueda_exhaustiva(self.problema, limite=20)

    def test_exhaustiva_sin_combinaciones_validas(self):
        corto = Escenario.desde_listas([[1, 1, 1]], (0, 0), [(0, 2)])
        problema = crear_problema(corto, [(0, 0)], ParametrosAG(k=2, d_min=3))
        self.assertIsNone(x.busqueda_exhaustiva(problema))

    def test_azar_reproducible_y_acotado(self):
        a = x.mejor_al_azar(self.problema, 5, semilla=2)
        self.assertEqual(a, x.mejor_al_azar(self.problema, 5, semilla=2))
        self.assertLessEqual(a, 0.5 + 1e-12)
        with self.assertRaises(ValueError):
            x.mejor_al_azar(self.problema, 0)

    def test_comparar(self):
        fila = x.comparar("Pasillo", PASILLO, GRUPO_CENTRO, PARAMS, semillas=(1, 2, 3))
        self.assertEqual((fila.dimensiones, fila.k, fila.semillas), ("1x7", 2, 3))
        self.assertLessEqual(fila.ag_min, fila.ag_media)
        self.assertLessEqual(fila.ag_media, fila.ag_max)
        self.assertAlmostEqual(fila.exhaustivo, 0.5)
        self.assertLessEqual(fila.ag_max, fila.exhaustivo + 1e-12)
        self.assertLessEqual(fila.azar_max, fila.exhaustivo + 1e-12)
        sin_ex = x.comparar("Pasillo", PASILLO, GRUPO_CENTRO, PARAMS, semillas=(1,),
                            exhaustivo=False)
        self.assertIsNone(sin_ex.exhaustivo)
        texto = x.tabla_markdown([fila, sin_ex])
        self.assertIn("| Pasillo | 1x7 | 2 | 3 |", texto)
        self.assertTrue(texto.splitlines()[-1].endswith("| - |"))
        self.assertEqual(len(x.tabla_csv([fila]).splitlines()), 2)
        with self.assertRaises(ValueError):
            x.comparar("Pasillo", PASILLO, GRUPO_CENTRO, PARAMS, semillas=())


class TestTablas(unittest.TestCase):
    def setUp(self):
        self.resultado = optimizar(PASILLO, GRUPO_CENTRO, PARAMS)

    def test_historial(self):
        filas = list(csv.reader(io.StringIO(x.historial_csv(self.resultado))))
        self.assertEqual(filas[0][0], "Generación")
        self.assertEqual(len(filas) - 1, PARAMS.generaciones + 1)  # incluye la generación 0
        resumido = x.historial_markdown(self.resultado, cada=2).splitlines()[2:]
        # Generaciones 0, 2, 4 y la última (5).
        self.assertEqual([l.split("|")[1].strip() for l in resumido], ["0", "2", "4", "5"])
        with self.assertRaises(ValueError):
            x.historial_markdown(self.resultado, cada=0)

    def test_top3(self):
        filas = list(csv.reader(io.StringIO(x.top3_csv(self.resultado))))
        self.assertEqual(len(filas) - 1, len(self.resultado.top3))
        primera = filas[1]
        self.assertEqual(primera[0], "1")
        self.assertEqual(primera[-1], str(self.resultado.evaluaciones))
        self.assertIn("(0,3)", primera[1])
        self.assertEqual(primera[2], "100.0")

    def test_top3_sin_ruta_no_divide_entre_cero(self):
        # El grupo queda aislado detrás de un muro: O1 = 0 y tiempos 0.
        esc = Escenario.desde_listas([[1, 1, 1, 1], [0, 0, 0, 0], [5, 5, 5, 5]],
                                     (0, 0), [(0, 3)])
        res = optimizar(esc, [(2, 0, 3)], ParametrosAG(k=2, d_min=3, tam_poblacion=4,
                                                       generaciones=2, semilla=1))
        self.assertIn("| 0.0 |", x.top3_markdown(res))


class TestCliOptimizar(unittest.TestCase):
    DATA = Path(__file__).resolve().parent.parent / "data"

    def _correr(self, *args):
        base = ["optimizar", str(self.DATA / "a_sin_humo.csv"),
                "--grupos", str(self.DATA / "grupos_a.csv"), "--generaciones", "2"]
        salida, errores = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(errores):
            codigo = cli.main(base + list(args))
        return codigo, salida.getvalue(), errores.getvalue()

    def test_guarda_csv_sin_graficos(self):
        with tempfile.TemporaryDirectory() as tmp:
            codigo, salida, _ = self._correr("--semilla", "7", "--salida", tmp)
            self.assertEqual(codigo, 0)
            self.assertIn("Tres mejores configuraciones", salida)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()),
                             ["historial.csv", "top3.csv"])

    def test_errores_esperables_devuelven_1(self):
        for args, mensaje in ((["--k", "5"], "k debe estar"),
                              (["--grafico"], "--salida"),
                              (["--p-evac", "0"], "p_evac")):
            with self.subTest(args=args):
                codigo, _, errores = self._correr(*args)
                self.assertEqual(codigo, 1)
                self.assertIn(mensaje, errores)


if __name__ == "__main__":
    unittest.main()


class TestAjuste(unittest.TestCase):
    def setUp(self):
        self.filas = x.barrido_parametros(
            escenarios=[("Pasillo", PASILLO, GRUPO_CENTRO)], ks=(2,), sigmas=(0.10, 0.30), elitismos=(1, 2),
            semillas=range(3), base=PARAMS)

    def test_una_fila_por_combinacion(self):
        combos = {(f.k, f.sigma, f.elitismo) for f in self.filas}
        self.assertEqual(combos, {(2, 0.10, 1), (2, 0.10, 2), (2, 0.30, 1), (2, 0.30, 2)})
        self.assertEqual(len(self.filas), 4)

    def test_estadisticas_coherentes(self):
        for f in self.filas:
            self.assertEqual(f.semillas, 3)
            self.assertLessEqual(f.aptitud_min, f.aptitud_media + 1e-12)
            self.assertLessEqual(f.aptitud_media, f.aptitud_max + 1e-12)
            self.assertLessEqual(f.aptitud_max, 0.5 + 1e-12)       # tope del pasillo
            self.assertGreaterEqual(f.ultima_mejora_media, 0)
            self.assertLessEqual(f.ultima_mejora_media, PARAMS.generaciones)

    def test_es_determinista(self):
        otra = x.barrido_parametros(
            escenarios=[("Pasillo", PASILLO, GRUPO_CENTRO)], ks=(2,), sigmas=(0.10, 0.30), elitismos=(1, 2),
            semillas=range(3), base=PARAMS)
        self.assertEqual(otra, self.filas)

    def test_sin_semillas_se_rechaza(self):
        with self.assertRaises(ValueError):
            x.barrido_parametros(escenarios=[("Pasillo", PASILLO, GRUPO_CENTRO)], semillas=[])

    def test_tablas(self):
        csv_texto = x.ajuste_csv(self.filas)
        lineas = list(csv.reader(io.StringIO(csv_texto)))
        self.assertEqual(len(lineas), 1 + len(self.filas))
        self.assertEqual(lineas[0][:4], ["Escenario", "k", "Sigma", "Élites"])
        self.assertIn("| Pasillo | 2 | 0.30 |", x.ajuste_markdown(self.filas))

    def test_cli_ajuste_ag_escribe_csv(self):
        with tempfile.TemporaryDirectory() as carpeta:
            destino = Path(carpeta) / "ajuste.csv"
            salida = io.StringIO()
            with contextlib.redirect_stdout(salida):
                codigo = cli.main(["ajuste-ag", "--k", "2", "--sigmas", "0.3",
                                   "--elitismos", "2", "--semillas", "1", "--desde", "5",
                                   "--csv", str(destino)])
            self.assertEqual(codigo, 0)
            self.assertTrue(destino.read_text(encoding="utf-8").startswith("Escenario,k,Sigma"))

