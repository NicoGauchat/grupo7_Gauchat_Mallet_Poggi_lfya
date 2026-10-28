"""Normalización y serialización de AST de funciones para comparar su estructura."""

import ast
import copy


def normalizar_funcion(nodo):
    """Devuelve una copia normalizada de un FunctionDef sin alterar el original.

    Usa un mapa de nombres por función, sin resolver ámbitos semánticos.
    El resultado es una representación para comparar, no para ejecutar.
    """
    copia = copy.deepcopy(nodo)
    return _Normalizador(copia).visit(copia)


def serializar_ast(nodo_normalizado):
    """Devuelve tokens en pre-order sin modificar el árbol normalizado.

    Los marcadores conservan los campos y los límites de nodos y listas.
    Las posiciones y los comentarios de tipo no participan en la comparación.
    """
    tokens = []

    def recorrer(elemento):
        if isinstance(elemento, ast.AST):
            tokens.append(f"NODO:{type(elemento).__name__}")
            for campo, valor in ast.iter_fields(elemento):
                if campo == "type_comment":
                    continue
                tokens.append(f"CAMPO:{campo}")
                recorrer(valor)
            tokens.append("FIN_NODO")
        elif isinstance(elemento, list):
            tokens.append("INICIO_LISTA")
            for valor in elemento:
                recorrer(valor)
            tokens.append("FIN_LISTA")
        elif elemento is None:
            tokens.append("AUSENTE")
        else:
            tokens.append(f"VALOR:{elemento!r}")

    recorrer(nodo_normalizado)
    return tokens


class _Normalizador(ast.NodeTransformer):
    def __init__(self, raiz):
        self.raiz = raiz
        self.nombres = {}

    def _normalizar_nombre(self, nombre):
        if nombre is None:
            return None
        if nombre not in self.nombres:
            self.nombres[nombre] = f"VAR{len(self.nombres) + 1}"
        return self.nombres[nombre]

    def generic_visit(self, nodo):
        if hasattr(nodo, "type_comment"):
            nodo.type_comment = None
        return super().generic_visit(nodo)

    def visit_FunctionDef(self, nodo):
        if nodo is self.raiz:
            nodo.name = "FUNCION"
        else:
            nodo.name = self._normalizar_nombre(nodo.name)
        # Detectar el docstring antes de reemplazar sus constantes por LIT.
        if ast.get_docstring(nodo, clean=False) is not None:
            nodo.body.pop(0)
        return self.generic_visit(nodo)

    def visit_AsyncFunctionDef(self, nodo):
        return self.visit_FunctionDef(nodo)

    def visit_arguments(self, nodo):
        parametros = nodo.posonlyargs + nodo.args
        if nodo.vararg is not None:
            parametros.append(nodo.vararg)
        parametros.extend(nodo.kwonlyargs)
        if nodo.kwarg is not None:
            parametros.append(nodo.kwarg)

        # Registrar todos primero: anotaciones y defaults pueden contener nombres.
        for parametro in parametros:
            self._normalizar_nombre(parametro.arg)
        return self.generic_visit(nodo)

    def visit_arg(self, nodo):
        nodo.arg = self._normalizar_nombre(nodo.arg)
        return self.generic_visit(nodo)

    def visit_Name(self, nodo):
        nodo.id = self._normalizar_nombre(nodo.id)
        return self.generic_visit(nodo)

    def visit_Constant(self, nodo):
        nodo.value = "LIT"
        nodo.kind = None
        return self.generic_visit(nodo)

    def visit_ClassDef(self, nodo):
        nodo.name = self._normalizar_nombre(nodo.name)
        return self.generic_visit(nodo)

    def visit_alias(self, nodo):
        nodo.asname = self._normalizar_nombre(nodo.asname)
        return self.generic_visit(nodo)

    def visit_ExceptHandler(self, nodo):
        # El tipo aparece antes del nombre capturado en los campos del AST.
        if nodo.type is not None:
            nodo.type = self.visit(nodo.type)
        nodo.name = self._normalizar_nombre(nodo.name)
        nodo.body = [self.visit(instruccion) for instruccion in nodo.body]
        return nodo

    def visit_Global(self, nodo):
        nodo.names = [self._normalizar_nombre(nombre) for nombre in nodo.names]
        return self.generic_visit(nodo)

    def visit_Nonlocal(self, nodo):
        nodo.names = [self._normalizar_nombre(nombre) for nombre in nodo.names]
        return self.generic_visit(nodo)

    def visit_MatchAs(self, nodo):
        self.generic_visit(nodo)
        nodo.name = self._normalizar_nombre(nodo.name)
        return nodo

    def visit_MatchStar(self, nodo):
        nodo.name = self._normalizar_nombre(nodo.name)
        return self.generic_visit(nodo)

    def visit_MatchMapping(self, nodo):
        self.generic_visit(nodo)
        nodo.rest = self._normalizar_nombre(nodo.rest)
        return nodo

    def visit_TypeVar(self, nodo):
        nodo.name = self._normalizar_nombre(nodo.name)
        return self.generic_visit(nodo)

    def visit_ParamSpec(self, nodo):
        nodo.name = self._normalizar_nombre(nodo.name)
        return self.generic_visit(nodo)

    def visit_TypeVarTuple(self, nodo):
        nodo.name = self._normalizar_nombre(nodo.name)
        return self.generic_visit(nodo)
