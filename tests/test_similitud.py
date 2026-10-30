from pathlib import Path
import unittest

from extractor import extraer_funciones
from normalizador import normalizar_funcion, serializar_ast
from similitud import calcular_similitud, UMBRAL_SIMILITUD


class TestCasosObligatorios(unittest.TestCase):
    def setUp(self):
        directorio = Path(__file__).resolve().parent.parent / "ejemplos"
        funciones, errores = extraer_funciones(directorio)
        self.assertEqual(errores, [])
        self.tokens = {}
        for funcion in funciones:
            normalizado = normalizar_funcion(funcion["nodo"])
            self.tokens[funcion["nombre"]] = serializar_ast(normalizado)

    def test_positivo_clon_aritmetico(self):
        a = self.tokens["sumar"]
        b = self.tokens["total"]
        self.assertEqual(a, b)
        score = calcular_similitud(a, b)
        self.assertEqual(score, 1.0)
        self.assertGreaterEqual(score, UMBRAL_SIMILITUD)

    def test_positivo_clon_con_control_de_flujo(self):
        a = self.tokens["acumular"]
        b = self.tokens["contar"]
        self.assertEqual(a, b)
        score = calcular_similitud(a, b)
        self.assertEqual(score, 1.0)
        self.assertGreaterEqual(score, UMBRAL_SIMILITUD)

    def test_negativo_aritmetica_frente_a_recorrido_condicional(self):
        score = calcular_similitud(self.tokens["sumar"], self.tokens["contar"])
        self.assertLess(score, UMBRAL_SIMILITUD)

    def test_negativo_retorno_simple_frente_a_bucle_acumulador(self):
        score = calcular_similitud(self.tokens["identidad"], self.tokens["acumular"])
        self.assertLess(score, UMBRAL_SIMILITUD)
