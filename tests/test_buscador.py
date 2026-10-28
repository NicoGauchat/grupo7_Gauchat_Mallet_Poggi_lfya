"""Pruebas de la función buscar() del módulo buscar_similares."""

import os
import sys
import tempfile
import unittest

# Permite importar los módulos desde la raíz del proyecto
# aunque el runner se ejecute desde cualquier carpeta.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from buscar_similares import buscar


class PruebasBuscador(unittest.TestCase):

    def setUp(self):
        """Crea una carpeta temporal con archivos .py antes de cada prueba."""
        self.directorio_temp = tempfile.mkdtemp()

    def tearDown(self):
        """Elimina la carpeta temporal y su contenido al terminar cada prueba."""
        import shutil
        shutil.rmtree(self.directorio_temp)

    def _escribir_archivo(self, nombre, contenido):
        """Crea un archivo .py dentro de la carpeta temporal."""
        ruta = os.path.join(self.directorio_temp, nombre)
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as archivo:
            archivo.write(contenido)
        return nombre

    # --- Casos positivos obligatorios ---

    def test_clon_aritmetico_aparece_primero(self):
        """Un clon con variables renombradas debe tener score 1 y ser candidato."""
        self._escribir_archivo("funciones.py", """\
def sumar(a, b):
    resultado = a + b
    return resultado

def total(x, y):
    valor = x + y
    return valor
""")
        resultados, _ = buscar(
            self.directorio_temp,
            "funciones.py",
            "sumar",
            None,
            5,
        )

        self.assertGreater(len(resultados), 0)
        primero = resultados[0]
        self.assertEqual(primero["nombre"], "total")
        self.assertAlmostEqual(primero["score"], 1.0)
        self.assertTrue(primero["es_candidato"])

    def test_clon_con_control_de_flujo_es_candidato(self):
        """Dos funciones con bucle y condicional idénticos deben ser candidatos."""
        self._escribir_archivo("funciones.py", """\
def acumular(valores):
    total = 0
    for elemento in valores:
        if elemento > 5:
            total += elemento
    return total

def contar(datos):
    suma = 0
    for numero in datos:
        if numero > 5:
            suma += numero
    return suma
""")
        resultados, _ = buscar(
            self.directorio_temp,
            "funciones.py",
            "acumular",
            None,
            5,
        )

        self.assertGreater(len(resultados), 0)
        self.assertAlmostEqual(resultados[0]["score"], 1.0)
        self.assertTrue(resultados[0]["es_candidato"])

    # --- Casos negativos obligatorios ---

    def test_funcion_distinta_no_es_candidato(self):
        """Una función aritmética simple y un bucle con condicional no son candidatos."""
        self._escribir_archivo("funciones.py", """\
def sumar(a, b):
    resultado = a + b
    return resultado

def contar(datos):
    suma = 0
    for numero in datos:
        if numero > 5:
            suma += numero
    return suma
""")
        resultados, _ = buscar(
            self.directorio_temp,
            "funciones.py",
            "sumar",
            None,
            5,
        )

        self.assertGreater(len(resultados), 0)
        self.assertLess(resultados[0]["score"], 0.70)
        self.assertFalse(resultados[0]["es_candidato"])

    def test_retorno_simple_vs_bucle_no_es_candidato(self):
        """Un retorno directo y un bucle acumulador deben tener score bajo."""
        self._escribir_archivo("funciones.py", """\
def identidad(valor):
    return valor

def acumular(valores):
    total = 0
    for elemento in valores:
        if elemento > 5:
            total += elemento
    return total
""")
        resultados, _ = buscar(
            self.directorio_temp,
            "funciones.py",
            "identidad",
            None,
            5,
        )

        self.assertGreater(len(resultados), 0)
        self.assertLess(resultados[0]["score"], 0.70)
        self.assertFalse(resultados[0]["es_candidato"])

    # --- Comportamiento del buscador ---

    def test_funcion_inexistente_lanza_error(self):
        """Buscar una función que no existe debe lanzar ValueError."""
        self._escribir_archivo("funciones.py", """\
def sumar(a, b):
    return a + b
""")
        with self.assertRaises(ValueError):
            buscar(
                self.directorio_temp,
                "funciones.py",
                "no_existe",
                None,
                5,
            )

    def test_directorio_invalido_lanza_error(self):
        """Un directorio inexistente debe lanzar ValueError."""
        with self.assertRaises(ValueError):
            buscar(
                "/ruta/que/no/existe",
                "archivo.py",
                "funcion",
                None,
                5,
            )

    def test_objetivo_excluido_de_resultados(self):
        """La función objetivo no debe aparecer en sus propios resultados."""
        self._escribir_archivo("funciones.py", """\
def sumar(a, b):
    resultado = a + b
    return resultado

def total(x, y):
    valor = x + y
    return valor
""")
        resultados, _ = buscar(
            self.directorio_temp,
            "funciones.py",
            "sumar",
            None,
            5,
        )

        for resultado in resultados:
            self.assertFalse(
                resultado["archivo"] == "funciones.py" and resultado["nombre"] == "sumar",
                "El objetivo no debe aparecer en los resultados.",
            )

    def test_top_k_limita_resultados(self):
        """El parámetro top_k debe limitar la cantidad de resultados devueltos."""
        self._escribir_archivo("funciones.py", """\
def f1(a):
    return a

def f2(a):
    return a

def f3(a):
    return a

def f4(a):
    return a
""")
        resultados, _ = buscar(
            self.directorio_temp,
            "funciones.py",
            "f1",
            None,
            2,
        )

        self.assertLessEqual(len(resultados), 2)

    def test_nombre_ambiguo_sin_linea_lanza_error(self):
        """Dos funciones con el mismo nombre en el mismo archivo requieren --linea."""
        self._escribir_archivo("funciones.py", """\
def helper(x):
    return x + 1

class A:
    def helper(self, x):
        return x * 2
""")
        with self.assertRaises(ValueError):
            buscar(
                self.directorio_temp,
                "funciones.py",
                "helper",
                None,
                5,
            )

    def test_sin_otros_candidatos_devuelve_lista_vacia(self):
        """Con una sola función en el repositorio, los resultados son vacíos."""
        self._escribir_archivo("funciones.py", """\
def unica(a, b):
    return a + b
""")
        resultados, _ = buscar(
            self.directorio_temp,
            "funciones.py",
            "unica",
            None,
            5,
        )

        self.assertEqual(resultados, [])


if __name__ == "__main__":
    unittest.main()
