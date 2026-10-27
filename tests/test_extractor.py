import ast
from pathlib import Path
from tempfile import TemporaryDirectory
import tokenize
import unittest
from unittest.mock import patch

from extractor import extraer_funciones


class TestExtractor(unittest.TestCase):
    def setUp(self):
        temporal = TemporaryDirectory()
        self.addCleanup(temporal.cleanup)
        self.directorio = Path(temporal.name)

    def crear_archivo(self, nombre, contenido, encoding="utf-8"):
        archivo = self.directorio / nombre
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(contenido, encoding=encoding)
        return archivo

    def test_funcion_simple_y_metadatos(self):
        self.crear_archivo(
            "sumas.py", "# Operaciones\n\ndef sumar(a, b):\n    return a + b\n"
        )

        for directorio in (self.directorio, str(self.directorio)):
            with self.subTest(directorio=directorio):
                funciones, errores = extraer_funciones(directorio)
                self.assertEqual(errores, [])
                self.assertEqual(len(funciones), 1)
                funcion = funciones[0]
                self.assertEqual(set(funcion), {"nombre", "archivo", "linea", "nodo"})
                self.assertEqual(funcion["nombre"], "sumar")
                self.assertEqual(funcion["archivo"], "sumas.py")
                self.assertEqual(funcion["linea"], 3)
                self.assertIsInstance(funcion["nodo"], ast.FunctionDef)
                self.assertEqual(funcion["nodo"].name, "sumar")
                self.assertEqual(funcion["nodo"].args.args[0].arg, "a")

    def test_subdirectorios_varias_funciones_y_orden(self):
        self.crear_archivo("z.py", "def ultima():\n    pass\n")
        self.crear_archivo("sub/a.py", "def interna():\n    pass\n")
        self.crear_archivo(
            "a.py", "def zeta():\n    pass\n\ndef alfa():\n    pass\n"
        )
        self.crear_archivo("ignorar.txt", "def no_extraer():\n    pass\n")

        funciones, errores = extraer_funciones(self.directorio)

        self.assertEqual(errores, [])
        self.assertEqual(
            [(f["archivo"], f["nombre"], f["linea"]) for f in funciones],
            [("a.py", "zeta", 1), ("a.py", "alfa", 4),
             ("sub/a.py", "interna", 1), ("z.py", "ultima", 1)],
        )
        repetidas, _ = extraer_funciones(self.directorio)
        self.assertEqual(
            [(f["archivo"], f["linea"]) for f in funciones],
            [(f["archivo"], f["linea"]) for f in repetidas],
        )

    def test_metodos_funciones_anidadas_y_nombres_repetidos(self):
        self.crear_archivo(
            "estructura.py",
            "class Primera:\n"
            "    def metodo(self):\n"
            "        def anidada():\n"
            "            pass\n"
            "        return anidada\n"
            "\n"
            "class Segunda:\n"
            "    def metodo(self):\n"
            "        pass\n",
        )

        funciones, errores = extraer_funciones(self.directorio)

        self.assertEqual(errores, [])
        self.assertEqual(
            [(f["nombre"], f["linea"]) for f in funciones],
            [("metodo", 2), ("anidada", 3), ("metodo", 8)],
        )
        self.assertIsInstance(funciones[0]["nodo"].body[0], ast.FunctionDef)

    def test_excluye_async_pero_extrae_functiondef_en_su_interior(self):
        self.crear_archivo(
            "async.py",
            "async def asincrona():\n"
            "    def sincrona():\n"
            "        pass\n"
            "    return sincrona\n",
        )

        funciones, errores = extraer_funciones(self.directorio)

        self.assertEqual(errores, [])
        self.assertEqual([f["nombre"] for f in funciones], ["sincrona"])

    def test_sintaxis_incorrecta_no_detiene_otros_archivos(self):
        self.crear_archivo("a_invalido.py", "def incompleta(\n")
        self.crear_archivo("z_valido.py", "def correcta():\n    pass\n")

        funciones, errores = extraer_funciones(self.directorio)

        self.assertEqual([f["nombre"] for f in funciones], ["correcta"])
        self.assertEqual(len(errores), 1)
        self.assertIn("a_invalido.py", errores[0])

    def test_respeta_codificacion_declarada(self):
        self.crear_archivo(
            "acentos.py",
            "# coding: latin-1\ndef saludar():\n    return 'ma\u00f1ana'\n",
            encoding="latin-1",
        )

        funciones, errores = extraer_funciones(self.directorio)

        self.assertEqual(errores, [])
        self.assertEqual(len(funciones), 1)
        self.assertEqual(funciones[0]["nodo"].body[0].value.value, "ma\u00f1ana")

    def test_codificacion_incorrecta_no_detiene_otros_archivos(self):
        (self.directorio / "a_invalido.py").write_bytes(
            b"# coding: utf-8\ndef saludar():\n    return '\xff'\n"
        )
        self.crear_archivo("z_valido.py", "def correcta():\n    pass\n")

        funciones, errores = extraer_funciones(self.directorio)

        self.assertEqual([f["nombre"] for f in funciones], ["correcta"])
        self.assertEqual(len(errores), 1)
        self.assertIn("a_invalido.py", errores[0])

    def test_error_de_lectura_no_detiene_otros_archivos(self):
        inaccesible = self.crear_archivo("a_inaccesible.py", "def oculta():\n    pass\n")
        self.crear_archivo("z_valido.py", "def correcta():\n    pass\n")
        abrir_original = tokenize.open

        # Simula el fallo sin depender de los permisos del sistema operativo.
        def abrir_con_error(archivo):
            if archivo == inaccesible:
                raise OSError("Lectura no disponible")
            return abrir_original(archivo)

        with patch("extractor.tokenize.open", side_effect=abrir_con_error):
            funciones, errores = extraer_funciones(self.directorio)

        self.assertEqual([f["nombre"] for f in funciones], ["correcta"])
        self.assertEqual(len(errores), 1)
        self.assertIn("a_inaccesible.py", errores[0])
        self.assertIn("Lectura no disponible", errores[0])

    def test_carpeta_vacia_y_archivo_sin_funciones(self):
        self.assertEqual(extraer_funciones(self.directorio), ([], []))
        self.crear_archivo("constantes.py", "VALOR = 3\n")
        self.assertEqual(extraer_funciones(self.directorio), ([], []))

    def test_rechaza_rutas_que_no_son_directorios(self):
        archivo = self.crear_archivo("archivo.py", "VALOR = 3\n")
        for ruta in (self.directorio / "inexistente", archivo):
            with self.subTest(ruta=ruta):
                with self.assertRaisesRegex(ValueError, "directorio existente"):
                    extraer_funciones(ruta)

    def test_no_ejecuta_el_codigo_analizado(self):
        self.crear_archivo(
            "sin_ejecutar.py",
            "raise RuntimeError('Este archivo no debe ejecutarse')\n"
            "def disponible():\n"
            "    pass\n",
        )

        funciones, errores = extraer_funciones(self.directorio)

        self.assertEqual(errores, [])
        self.assertEqual([f["nombre"] for f in funciones], ["disponible"])
