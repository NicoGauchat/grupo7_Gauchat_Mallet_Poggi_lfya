"""Similitud de Jaccard sobre n-gramas de tokens del AST normalizado."""

N_GRAMA = 3
UMBRAL_SIMILITUD = 0.70


def crear_ngramas(tokens, n=N_GRAMA):
    """Devuelve un conjunto de tuplas de n tokens consecutivos.

    Una secuencia no vacía más corta que n forma un único n-grama.
    """
    if n < 1:
        raise ValueError("El tamaño del n-grama debe ser positivo")
    if not tokens:
        return set()
    if len(tokens) < n:
        return {tuple(tokens)}

    ngramas = set()
    for inicio in range(len(tokens) - n + 1):
        ngrama = tuple(tokens[inicio:inicio + n])
        ngramas.add(ngrama)
    return ngramas


def calcular_similitud(tokens_a, tokens_b):
    """Calcula Jaccard entre 0 y 1; dos secuencias vacías puntúan 1."""
    ngramas_a = crear_ngramas(tokens_a)
    ngramas_b = crear_ngramas(tokens_b)
    union = ngramas_a | ngramas_b

    if not union:
        return 1.0

    interseccion = ngramas_a & ngramas_b
    return len(interseccion) / len(union)
