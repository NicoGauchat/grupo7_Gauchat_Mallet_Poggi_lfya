from pathlib import Path
import unittest

from extractor import extraer_funciones
from normalizador import normalizar_funcion, serializar_ast
from similitud import crear_ngramas, calcular_similitud, UMBRAL_SIMILITUD


class TestSimilitud(unittest.TestCase):
    def test_ngramas_consecutivos_sin_repeticiones(self):
        self.assertEqual(crear_ngramas(["a", "b", "a", "b", "a"]), {
            ("a", "b", "a"), ("b", "a", "b"),
        })

    def test_ngramas_vacios_cortos_y_tamano_exacto(self):
        self.assertEqual(crear_ngramas([]), set())
        self.assertEqual(crear_ngramas(["a"]), {("a",)})
        self.assertEqual(crear_ngramas(["a", "b"]), {("a", "b")})
        self.assertEqual(crear_ngramas(["a", "b", "c"]), {("a", "b", "c")})

    def test_otros_tamanos_y_tamano_invalido(self):
        self.assertEqual(crear_ngramas(["a", "b", "c"], n=2), {
            ("a", "b"), ("b", "c"),
        })
        for n in (0, -1):
            with self.subTest(n=n):
                with self.assertRaises(ValueError):
                    crear_ngramas(["a"], n=n)

    def test_formula_de_jaccard(self):
        # Comparten (a, b, c); la unión tiene tres n-gramas distintos.
        a = ["a", "b", "c", "d"]
        b = ["a", "b", "c", "e"]

        self.assertAlmostEqual(calcular_similitud(a, b), 1 / 3)

    def test_vacios_y_secuencias_cortas(self):
        self.assertEqual(calcular_similitud([], []), 1.0)
        self.assertEqual(calcular_similitud([], ["a"]), 0.0)
        self.assertEqual(calcular_similitud(["a"], []), 0.0)
        self.assertEqual(calcular_similitud(["a", "b"], ["a", "b"]), 1.0)
        self.assertEqual(calcular_similitud(["a"], ["b"]), 0.0)
        self.assertEqual(calcular_similitud(["a"], ["a", "b"]), 0.0)

    def test_identidad_simetria_y_rango(self):
        secuencias = [[], ["a"], ["b"], ["a", "b", "c", "d"],
                      ["a", "b", "c", "e"]]
        for a in secuencias:
            self.assertEqual(calcular_similitud(a, a), 1.0)
            for b in secuencias:
                with self.subTest(a=a, b=b):
                    score = calcular_similitud(a, b)
                    self.assertEqual(score, calcular_similitud(b, a))
                    self.assertGreaterEqual(score, 0.0)
                    self.assertLessEqual(score, 1.0)

    def test_no_modifica_los_tokens(self):
        a = ["a", "b", "c", "d"]
        b = ["a", "b", "c", "e"]
        antes_a = a.copy()
        antes_b = b.copy()

        calcular_similitud(a, b)

        self.assertEqual(a, antes_a)
        self.assertEqual(b, antes_b)

    def test_jaccard_no_cuenta_repeticiones(self):
        self.assertEqual(calcular_similitud(["a"] * 3, ["a"] * 6), 1.0)


class TestCalibracion(unittest.TestCase):
    def setUp(self):
        directorio = Path(__file__).resolve().parent.parent / "ejemplos"
        funciones, errores = extraer_funciones(directorio)
        self.assertEqual(errores, [])
        self.tokens = {}
        for funcion in funciones:
            normalizado = normalizar_funcion(funcion["nodo"])
            self.tokens[funcion["nombre"]] = serializar_ast(normalizado)

    def test_dos_positivos_con_renombrado(self):
        for a, b in (("sumar", "total"), ("acumular", "contar")):
            with self.subTest(a=a, b=b):
                self.assertEqual(self.tokens[a], self.tokens[b])
                score = calcular_similitud(self.tokens[a], self.tokens[b])
                self.assertEqual(score, 1.0)
                self.assertGreaterEqual(score, UMBRAL_SIMILITUD)

    def test_dos_negativos_estructuralmente_distintos(self):
        for a, b in (("sumar", "contar"), ("identidad", "acumular")):
            with self.subTest(a=a, b=b):
                score = calcular_similitud(self.tokens[a], self.tokens[b])
                self.assertLess(score, UMBRAL_SIMILITUD)

    def test_reordenamiento_exploratorio(self):
        a = self.tokens["operaciones"]
        b = self.tokens["operaciones_reordenadas"]

        self.assertNotEqual(a, b)
        score = calcular_similitud(a, b)
        # En este ejemplo cambia el orden, pero no el conjunto de trigramas.
        self.assertEqual(score, 1.0)
