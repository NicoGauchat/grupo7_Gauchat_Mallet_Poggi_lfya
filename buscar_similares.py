import argparse
import sys
from pathlib import Path
from extractor import extraer_funciones
from normalizador import normalizar_funcion, serializar_ast
from similitud import calcular_similitud, UMBRAL_SIMILITUD


def buscar(directorio, archivo_objetivo, nombre_objetivo, linea_objetivo, top_k):


    if top_k < 1:
        raise ValueError("La cantidad de resultados debe ser un entero positivo.")
    directorio = Path(directorio).resolve()
    archivo = Path(archivo_objetivo)
    mensaje_ruta = "El archivo objetivo debe ser una ruta relativa dentro del directorio."
    if archivo.is_absolute() or archivo.drive or archivo.root:
        raise ValueError(mensaje_ruta)
    try:
        archivo_objetivo = (directorio / archivo).resolve().relative_to(directorio).as_posix()
    except ValueError:
        raise ValueError(mensaje_ruta) from None

    funciones, errores = extraer_funciones(directorio)

    def error_de_seleccion(mensaje):

        avisos = [f"Aviso: {error}" for error in errores]
        return ValueError("\n".join([mensaje] + avisos))

    if not funciones:
        raise error_de_seleccion("No se encontraron funciones en el directorio indicado.")

    candidatos_objetivo = [
        f for f in funciones
        if f["archivo"] == archivo_objetivo and f["nombre"] == nombre_objetivo
    ]
    if not candidatos_objetivo:
        raise error_de_seleccion(
            f"No se encontró '{nombre_objetivo}' en '{archivo_objetivo}'."
        )
    if len(candidatos_objetivo) > 1 and linea_objetivo is None:
        lineas = [str(f["linea"]) for f in candidatos_objetivo]
        raise error_de_seleccion(
            f"El nombre '{nombre_objetivo}' aparece en más de una línea "
            f"de '{archivo_objetivo}': {', '.join(lineas)}. "
            f"Usá --linea para indicar cuál."
        )
    if linea_objetivo is not None:
        candidatos_objetivo = [
            f for f in candidatos_objetivo if f["linea"] == linea_objetivo
        ]
        if not candidatos_objetivo:
            raise error_de_seleccion(
                f"No se encontró '{nombre_objetivo}' en línea {linea_objetivo} "
                f"de '{archivo_objetivo}'."
            )
    objetivo = candidatos_objetivo[0]

    tokens_objetivo = serializar_ast(normalizar_funcion(objetivo["nodo"]))

    resultados = []
    for funcion in funciones:
        if funcion["archivo"] == objetivo["archivo"] and funcion["linea"] == objetivo["linea"]:
            continue
        tokens_otra = serializar_ast(normalizar_funcion(funcion["nodo"]))
        score = calcular_similitud(tokens_objetivo, tokens_otra)
        resultados.append({
            "nombre": funcion["nombre"],
            "archivo": funcion["archivo"],
            "linea": funcion["linea"],
            "score": score,
            "es_candidato": score >= UMBRAL_SIMILITUD,
        })

    resultados.sort(key=lambda r: (-r["score"], r["archivo"], r["linea"]))
    return resultados[:top_k], errores


def main():

    parser = argparse.ArgumentParser(
        description="Busca funciones de estructura similar en un repositorio Python."
    )
    parser.add_argument(
        "--dir",
        required=True,
        metavar="DIRECTORIO",
        help="Carpeta raíz con los archivos .py a analizar.",
    )
    parser.add_argument(
        "--funcion",
        required=True,
        metavar="ARCHIVO:NOMBRE",
        help="Función objetivo en formato 'archivo.py:nombre'. "
             "El archivo es relativo al directorio indicado.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        metavar="K",
        help="Cantidad de resultados a mostrar (predeterminado: 5).",
    )
    parser.add_argument(
        "--linea",
        type=int,
        default=None,
        metavar="NUMERO",
        help="Línea de la función objetivo para resolver ambigüedades de nombre.",
    )
    args = parser.parse_args()

    if args.top < 1:
        print("Error: --top debe ser un entero positivo.", file=sys.stderr)
        sys.exit(1)

    if ":" not in args.funcion:
        print(
            "Error: --funcion debe tener el formato 'archivo.py:nombre'.",
            file=sys.stderr,
        )
        sys.exit(1)
    ultimo_dos_puntos = args.funcion.rfind(":")
    archivo_objetivo = args.funcion[:ultimo_dos_puntos]
    nombre_objetivo = args.funcion[ultimo_dos_puntos + 1:]
    if not archivo_objetivo or not nombre_objetivo:
        print(
            "Error: --funcion debe tener el formato 'archivo.py:nombre'.",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        resultados, avisos = buscar(
            args.dir,
            archivo_objetivo,
            nombre_objetivo,
            args.linea,
            args.top,
        )
    except ValueError as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

    for aviso in avisos:
        print(f"Aviso: {aviso}", file=sys.stderr)
    if not resultados:
        print("No se encontraron otras funciones para comparar.")
        return
    print(
        f"Top {len(resultados)} funciones más similares a "
        f"'{nombre_objetivo}' ({archivo_objetivo}):\n"
    )
    for posicion, resultado in enumerate(resultados, start=1):
        etiqueta = " [CANDIDATO A DUPLICADO]" if resultado["es_candidato"] else ""
        print(
            f"{posicion}. {resultado['archivo']}:{resultado['nombre']} "
            f"(línea {resultado['linea']}) — score: {resultado['score']:.4f}{etiqueta}"
        )


if __name__ == "__main__":
    main()
