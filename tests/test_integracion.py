"""Pruebas del flujo completo ejecutando la consola en un proceso real."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from buscar_similares import buscar


class TestIntegracion(unittest.TestCase):
    def setUp(self):
        temporal = tempfile.TemporaryDirectory(prefix="lfya integracion ")
        self.addCleanup(temporal.cleanup)
        self.directorio = Path(temporal.name)
        self.cli = Path(__file__).resolve().parent.parent / "buscar_similares.py"

    def escribir(self, nombre, codigo):
        archivo = self.directorio / nombre
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(codigo, encoding="utf-8")

    def ejecutar(self, objetivo="objetivo.py:objetivo", *opciones):
        return subprocess.run(
            [sys.executable, "-X", "utf8", "-B", str(self.cli),
             "--dir", str(self.directorio), "--funcion", objetivo, *opciones],
            cwd=self.directorio,
            capture_output=True, text=True, encoding="utf-8", timeout=10,
        )

    def test_top_grande_empates_subcarpetas_y_rutas_con_espacios(self):
        self.escribir("objetivo.py", "def objetivo(x):\n    return x\n")
        self.escribir("sub carpeta/a.py", "def copia(y):\n    return y\n\ndef copia(z):\n    return z\n")
        self.escribir("z.py", "def ultima(w):\n    return w\n")

        proceso = self.ejecutar("objetivo.py:objetivo", "--top", "50")

        self.assertEqual(proceso.returncode, 0, proceso.stderr)
        self.assertEqual(proceso.stderr, "")
        filas = [linea for linea in proceso.stdout.splitlines() if "score:" in linea]
        self.assertEqual(len(filas), 3)
        self.assertIn("1. sub carpeta/a.py:copia (línea 1)", filas[0])
        self.assertIn("2. sub carpeta/a.py:copia (línea 4)", filas[1])
        self.assertIn("3. z.py:ultima", filas[2])
        for fila in filas:
            self.assertIn("score: 1.0000 [CANDIDATO A DUPLICADO]", fila)

    def test_nombre_ambiguo_y_seleccion_por_linea(self):
        self.escribir("objetivo.py", "def objetivo(x):\n    return x\n\ndef objetivo(y):\n    return y\n")

        ambiguo = self.ejecutar()
        elegido = self.ejecutar("objetivo.py:objetivo", "--linea", "4")
        inexistente = self.ejecutar("objetivo.py:objetivo", "--linea", "99")

        self.assertNotEqual(ambiguo.returncode, 0)
        self.assertIn("1, 4", ambiguo.stderr)
        self.assertIn("--linea", ambiguo.stderr)
        self.assertEqual(elegido.returncode, 0, elegido.stderr)
        self.assertIn("objetivo.py:objetivo (línea 1)", elegido.stdout)
        self.assertNotEqual(inexistente.returncode, 0)
        self.assertIn("99", inexistente.stderr)

    def test_mezcla_archivos_validos_invalidos_y_codigo_no_ejecutado(self):
        self.escribir("objetivo.py", "raise RuntimeError('No ejecutar')\ndef objetivo(x):\n    return x\n")
        self.escribir("copia.py", "def copia(y):\n    return y\n")
        self.escribir("invalido.py", "def rota(\n")
        (self.directorio / "codificacion.py").write_bytes(b"# coding: utf-8\n\xff")

        proceso = self.ejecutar()

        self.assertEqual(proceso.returncode, 0, proceso.stderr)
        self.assertIn("copia.py:copia", proceso.stdout)
        self.assertIn("Aviso: invalido.py", proceso.stderr)
        self.assertIn("Aviso: codificacion.py", proceso.stderr)
        self.assertNotIn("Traceback", proceso.stderr)

    def test_carpeta_sin_funciones(self):
        proceso = self.ejecutar()

        self.assertNotEqual(proceso.returncode, 0)
        self.assertIn("No se encontraron funciones", proceso.stderr)
        self.assertEqual(proceso.stdout, "")

    def test_objetivo_sin_otras_funciones(self):
        self.escribir("objetivo.py", "def objetivo(x):\n    return x\n")

        proceso = self.ejecutar()

        self.assertEqual(proceso.returncode, 0, proceso.stderr)
        self.assertIn("No se encontraron otras funciones", proceso.stdout)

    def test_avisos_se_conservan_si_falla_la_seleccion(self):
        self.escribir("invalido.py", "def rota(\n")
        sin_funciones = self.ejecutar()
        self.escribir("otra.py", "def otra(x):\n    return x\n")
        sin_objetivo = self.ejecutar()

        for proceso in (sin_funciones, sin_objetivo):
            self.assertNotEqual(proceso.returncode, 0)
            self.assertIn("Error:", proceso.stderr)
            self.assertIn("Aviso: invalido.py", proceso.stderr)

    def test_errores_de_argumentos_y_objetivo_ausente(self):
        self.escribir("objetivo.py", "def objetivo(x):\n    return x\n")
        for objetivo in ("sin_separador", ":objetivo", "objetivo.py:", "objetivo.py:ausente"):
            with self.subTest(objetivo=objetivo):
                proceso = self.ejecutar(objetivo)
                self.assertNotEqual(proceso.returncode, 0)
                self.assertTrue(proceso.stderr)
                self.assertEqual(proceso.stdout, "")
        for k in ("0", "-1", "texto"):
            with self.subTest(k=k):
                proceso = self.ejecutar("objetivo.py:objetivo", "--top", k)
                self.assertNotEqual(proceso.returncode, 0)
                self.assertIn("--top", proceso.stderr)

    def test_directorio_inexistente(self):
        proceso = self.ejecutar("objetivo.py:objetivo", "--dir", str(self.directorio / "ausente"))

        self.assertNotEqual(proceso.returncode, 0)
        self.assertIn("directorio existente", proceso.stderr)

    def test_rutas_fuera_de_la_raiz(self):
        self.escribir("objetivo.py", "def objetivo(x):\n    return x\n")
        for archivo in ("../fuera.py", str(self.directorio / "objetivo.py")):
            with self.subTest(archivo=archivo):
                proceso = self.ejecutar(f"{archivo}:objetivo")
                self.assertNotEqual(proceso.returncode, 0)
                self.assertIn("ruta relativa dentro", proceso.stderr)

    def test_ruta_objetivo_con_separadores_del_sistema(self):
        self.escribir("sub carpeta/objetivo.py", "def objetivo(x):\n    return x\n")
        archivo = str(Path("sub carpeta") / "objetivo.py")

        proceso = self.ejecutar(f"{archivo}:objetivo")

        self.assertEqual(proceso.returncode, 0, proceso.stderr)

    def test_top_invalido_tambien_en_buscar(self):
        self.escribir("objetivo.py", "def objetivo(x):\n    return x\n")
        for k in (0, -1):
            with self.subTest(k=k):
                with self.assertRaisesRegex(ValueError, "positivo"):
                    buscar(self.directorio, "objetivo.py", "objetivo", None, k)
