"""Extracción de funciones de archivos Python sin ejecutar su código."""

import ast
from pathlib import Path
import tokenize


def extraer_funciones(directorio):
    """Devuelve (funciones, errores) al analizar una carpeta recursivamente.

    Cada función es un diccionario con nombre, archivo relativo, línea y nodo AST.
    Los errores de archivos individuales se devuelven como mensajes. Si la ruta
    inicial no es un directorio existente, se lanza ValueError.
    """
    directorio = Path(directorio)
    if not directorio.is_dir():
        raise ValueError(f"No es un directorio existente: {directorio}")

    funciones = []
    errores = []

    for archivo in sorted(directorio.rglob("*.py")):
        if not archivo.is_file():
            continue
        ruta_relativa = archivo.relative_to(directorio).as_posix()

        try:
            # Respeta la codificación declarada en el archivo, si la tiene.
            with tokenize.open(archivo) as fuente:
                codigo = fuente.read()
            arbol = ast.parse(codigo, filename=ruta_relativa)
        except (SyntaxError, UnicodeError, OSError) as error:
            errores.append(f"{ruta_relativa}: {error}")
            continue

        # También encuentra métodos y funciones dentro de otras funciones.
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.FunctionDef):
                funciones.append({
                    "nombre": nodo.name,
                    "archivo": ruta_relativa,
                    "linea": nodo.lineno,
                    "nodo": nodo,
                })

    funciones.sort(key=lambda funcion: (funcion["archivo"], funcion["linea"]))
    return funciones, errores
