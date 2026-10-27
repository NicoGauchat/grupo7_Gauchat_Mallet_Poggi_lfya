import ast
import unittest

from normalizador import normalizar_funcion


class TestNormalizador(unittest.TestCase):
    def normalizar_codigo(self, codigo):
        return normalizar_funcion(ast.parse(codigo, type_comments=True).body[0])

    def test_clones_aritmeticos_y_con_control_de_flujo(self):
        pares = [
            (
                "def sumar(a, b):\n    resultado = a + b\n    return resultado\n",
                "def total(x, y):\n    valor = x + y\n    return valor\n",
            ),
            (
                "def contar(valores):\n"
                "    total = 0\n"
                "    for elemento in valores:\n"
                "        if elemento > 5:\n"
                "            total += elemento\n"
                "    return total\n",
                "def acumular(datos):\n"
                "    suma = 10\n"
                "    for numero in datos:\n"
                "        if numero > 20:\n"
                "            suma += numero\n"
                "    return suma\n",
            ),
        ]
        for primero, segundo in pares:
            with self.subTest(codigo=primero):
                a = self.normalizar_codigo(primero)
                b = self.normalizar_codigo(segundo)
                self.assertEqual(ast.dump(a), ast.dump(b))
                self.assertEqual(a.name, "FUNCION")

    def test_conserva_correspondencias_y_operadores(self):
        base = self.normalizar_codigo("def f(a, b):\n    return a + b\n")
        for expresion in ("a + a", "a * b"):
            with self.subTest(expresion=expresion):
                diferente = self.normalizar_codigo(
                    f"def f(a, b):\n    return {expresion}\n"
                )
                self.assertNotEqual(ast.dump(base), ast.dump(diferente))
        self.assertIsInstance(base.body[0].value.op, ast.Add)
        self.assertIsInstance(base.body[0].value.left.ctx, ast.Load)

    def test_parametros_antes_de_anotaciones_y_defaults(self):
        nodo = self.normalizar_codigo(
            "@decorador\n"
            "def f(a, /, b: Tipo = valor, *args: Otra, c: Tercera = otro, "
            "**kwargs: Cuarta) -> Resultado:\n"
            "    return a, b, args, c, kwargs\n"
        )
        argumentos = nodo.args
        self.assertEqual(argumentos.posonlyargs[0].arg, "VAR1")
        self.assertEqual(argumentos.args[0].arg, "VAR2")
        self.assertEqual(argumentos.vararg.arg, "VAR3")
        self.assertEqual(argumentos.kwonlyargs[0].arg, "VAR4")
        self.assertEqual(argumentos.kwarg.arg, "VAR5")
        self.assertEqual(argumentos.args[0].annotation.id, "VAR6")
        self.assertEqual(
            [nombre.id for nombre in nodo.body[0].value.elts],
            ["VAR1", "VAR2", "VAR3", "VAR4", "VAR5"],
        )
        self.assertIsInstance(argumentos.defaults[0], ast.Name)
        self.assertIsInstance(argumentos.kw_defaults[0], ast.Name)
        self.assertIsInstance(nodo.returns, ast.Name)
        self.assertEqual(len(nodo.decorator_list), 1)

    def test_copia_original_posiciones_y_reinicio_del_mapa(self):
        original = ast.parse(
            "\n\ndef sumar(a):\n    resultado = a + 10\n    return resultado\n"
        ).body[0]
        antes = ast.dump(original, include_attributes=True)

        normalizado = normalizar_funcion(original)
        repetido = normalizar_funcion(original)

        self.assertEqual(ast.dump(original, include_attributes=True), antes)
        self.assertIsNot(normalizado, original)
        self.assertIsNot(normalizado.body[0], original.body[0])
        self.assertEqual(ast.dump(normalizado), ast.dump(repetido))
        self.assertEqual(normalizado.lineno, original.lineno)
        self.assertEqual(normalizado.body[0].col_offset, original.body[0].col_offset)
        self.assertEqual(normalizado.body[0].targets[0].id, "VAR2")
        self.assertIsInstance(normalizado.body[0].targets[0].ctx, ast.Store)

    def test_anidada_comparte_mapa_y_se_puede_normalizar_por_separado(self):
        original = ast.parse(
            "def externa(x):\n"
            "    def interna(y):\n"
            "        'Documentacion'\n"
            "        return x + y\n"
            "    return interna(x)\n"
        ).body[0]

        externa = normalizar_funcion(original)
        interna = externa.body[0]
        independiente = normalizar_funcion(original.body[0])

        self.assertEqual(interna.name, "VAR2")
        self.assertEqual(interna.args.args[0].arg, "VAR3")
        self.assertEqual(interna.body[0].value.left.id, "VAR1")
        self.assertEqual(interna.body[0].value.right.id, "VAR3")
        self.assertEqual(externa.body[1].value.func.id, "VAR2")
        self.assertEqual(independiente.name, "FUNCION")
        self.assertEqual(independiente.args.args[0].arg, "VAR1")
        self.assertEqual(independiente.body[0].value.left.id, "VAR2")
        self.assertEqual(original.body[0].name, "interna")

    def test_nombre_repetido_en_ambitos_comparte_token(self):
        nodo = self.normalizar_codigo(
            "def externa(x):\n"
            "    def interna(x):\n"
            "        return x\n"
            "    return x\n"
        )
        self.assertEqual(nodo.args.args[0].arg, "VAR1")
        self.assertEqual(nodo.body[0].args.args[0].arg, "VAR1")
        self.assertEqual(nodo.body[0].body[0].value.id, "VAR1")

    def test_clases_y_metodos(self):
        original = ast.parse(
            "def fabrica(valor):\n"
            "    class Caja:\n"
            "        def leer(self):\n"
            "            return valor\n"
            "    return Caja\n"
        ).body[0]
        nodo = normalizar_funcion(original)
        clase = nodo.body[0]
        metodo = clase.body[0]
        self.assertEqual(clase.name, "VAR2")
        self.assertEqual(metodo.name, "VAR3")
        self.assertEqual(metodo.args.args[0].arg, "VAR4")
        self.assertEqual(metodo.body[0].value.id, "VAR1")
        self.assertEqual(normalizar_funcion(original.body[0].body[0]).name, "FUNCION")

    def test_lambda_registra_parametros_antes_de_defaults(self):
        nodo = self.normalizar_codigo(
            "def externa(base):\n"
            "    return lambda a=base, *args, b=otro, **kwargs: (a, args, b, kwargs)\n"
        )
        funcion = nodo.body[0].value
        self.assertIsInstance(funcion, ast.Lambda)
        self.assertEqual(
            [nombre.id for nombre in funcion.body.elts],
            ["VAR2", "VAR3", "VAR4", "VAR5"],
        )
        self.assertEqual(funcion.args.defaults[0].id, "VAR1")
        self.assertEqual(funcion.args.kw_defaults[0].id, "VAR6")

    def test_async_interna_conserva_tipo_y_pierde_docstring(self):
        nodo = self.normalizar_codigo(
            "def externa(x):\n"
            "    async def interna(y):\n"
            "        'Documentacion'\n"
            "        return x + y\n"
            "    return interna\n"
        )
        interna = nodo.body[0]
        self.assertIsInstance(interna, ast.AsyncFunctionDef)
        self.assertEqual(interna.name, "VAR2")
        self.assertEqual(interna.args.args[0].arg, "VAR3")
        self.assertEqual(len(interna.body), 1)
        self.assertIsInstance(interna.body[0], ast.Return)

    def test_recursion_renombrada(self):
        primero = self.normalizar_codigo(
            "def factorial(n):\n"
            "    if n <= 1:\n"
            "        return 1\n"
            "    return n * factorial(n - 1)\n"
        )
        segundo = self.normalizar_codigo(
            "def calcular(x):\n"
            "    if x <= 1:\n"
            "        return 1\n"
            "    return x * calcular(x - 1)\n"
        )
        self.assertEqual(ast.dump(primero), ast.dump(segundo))
        self.assertEqual(primero.body[1].value.right.func.id, "VAR2")

    def test_constantes_y_solo_docstring_inicial(self):
        nodo = self.normalizar_codigo(
            "def f(valor):\n"
            "    'Documentacion'\n"
            "    if valor:\n"
            "        'Conservar esta expresion'\n"
            "    return (1, 3.5, 1j, 'texto', b'bytes', True, False, None, ..., u'texto')\n"
        )
        self.assertEqual(len(nodo.body), 2)
        self.assertIsInstance(nodo.body[0].body[0], ast.Expr)
        constantes = [n for n in ast.walk(nodo) if isinstance(n, ast.Constant)]
        self.assertEqual(len(constantes), 11)
        for constante in constantes:
            self.assertEqual(constante.value, "LIT")
            self.assertIsNone(constante.kind)
        solo_docstring = self.normalizar_codigo("def f():\n    ''\n")
        self.assertEqual(solo_docstring.body, [])

    def test_elimina_comentarios_de_tipo(self):
        original = ast.parse(
            "def f(\n"
            "    a,  # type: int\n"
            "):  # type: (int) -> int\n"
            "    x = a  # type: int\n"
            "    return x\n",
            type_comments=True,
        ).body[0]
        self.assertEqual(original.type_comment, "(int) -> int")
        self.assertEqual(original.args.args[0].type_comment, "int")

        nodo = normalizar_funcion(original)

        for parte in ast.walk(nodo):
            if hasattr(parte, "type_comment"):
                self.assertIsNone(parte.type_comment)
        self.assertEqual(original.body[0].type_comment, "int")

    def test_alias_atributos_modulos_y_etiquetas_de_llamadas(self):
        nodo = self.normalizar_codigo(
            "def f(obj):\n"
            "    import math as calculo\n"
            "    from paquete import transformar as convertir\n"
            "    import os\n"
            "    return obj.metodo(calculo.pi, convertir(obj), etiqueta=obj, **opciones)\n"
        )
        self.assertEqual(nodo.body[0].names[0].name, "math")
        self.assertEqual(nodo.body[0].names[0].asname, "VAR2")
        self.assertEqual(nodo.body[1].module, "paquete")
        self.assertEqual(nodo.body[1].names[0].name, "transformar")
        self.assertEqual(nodo.body[1].names[0].asname, "VAR3")
        self.assertEqual(nodo.body[2].names[0].name, "os")
        self.assertIsNone(nodo.body[2].names[0].asname)
        llamada = nodo.body[3].value
        self.assertEqual(llamada.func.attr, "metodo")
        self.assertEqual(llamada.func.value.id, "VAR1")
        self.assertEqual(llamada.args[0].attr, "pi")
        self.assertEqual(llamada.args[0].value.id, "VAR2")
        self.assertEqual(llamada.args[1].func.id, "VAR3")
        self.assertEqual(llamada.keywords[0].arg, "etiqueta")
        self.assertIsNone(llamada.keywords[1].arg)

    def test_global_nonlocal_y_nombres_de_excepciones(self):
        contenedora = ast.parse(
            "def contenedora():\n"
            "    externo = 1\n"
            "    def objetivo(valor):\n"
            "        global total\n"
            "        nonlocal externo\n"
            "        try:\n"
            "            total = valor\n"
            "        except ValueError as error:\n"
            "            return error\n"
            "        except:\n"
            "            pass\n"
            "        return externo\n"
        ).body[0]
        nodo = normalizar_funcion(contenedora.body[1])
        self.assertEqual(nodo.body[0].names, ["VAR2"])
        self.assertEqual(nodo.body[1].names, ["VAR3"])
        excepcion = nodo.body[2].handlers[0]
        self.assertEqual(excepcion.type.id, "VAR4")
        self.assertEqual(excepcion.name, "VAR5")
        self.assertEqual(excepcion.body[0].value.id, "VAR5")
        self.assertIsNone(nodo.body[2].handlers[1].name)
        self.assertEqual(nodo.body[3].value.id, "VAR3")

    def test_capturas_de_patrones_y_nombres_ausentes(self):
        nodo = self.normalizar_codigo(
            "def f(dato):\n"
            "    match dato:\n"
            "        case {'clave': valor, **resto}:\n"
            "            return valor, resto\n"
            "        case [primero, *otros] as captura:\n"
            "            return primero, otros, captura\n"
            "        case [*_]:\n"
            "            return None\n"
            "        case _:\n"
            "            return None\n"
        )
        casos = nodo.body[0].cases
        self.assertEqual(casos[0].pattern.patterns[0].name, "VAR2")
        self.assertEqual(casos[0].pattern.rest, "VAR3")
        self.assertEqual(casos[1].pattern.pattern.patterns[0].name, "VAR4")
        self.assertEqual(casos[1].pattern.pattern.patterns[1].name, "VAR5")
        self.assertEqual(casos[1].pattern.name, "VAR6")
        self.assertEqual(
            [n.id for n in casos[1].body[0].value.elts], ["VAR4", "VAR5", "VAR6"]
        )
        self.assertIsNone(casos[2].pattern.patterns[0].name)
        self.assertIsNone(casos[3].pattern.name)

    def test_parametros_de_tipo_y_sus_expresiones(self):
        nodo = self.normalizar_codigo("def f[T, *Ts, **P](dato: T):\n    return dato\n")
        self.assertIsInstance(nodo.type_params[0], ast.TypeVar)
        self.assertIsInstance(nodo.type_params[1], ast.TypeVarTuple)
        self.assertIsInstance(nodo.type_params[2], ast.ParamSpec)
        self.assertEqual([p.name for p in nodo.type_params], ["VAR2", "VAR3", "VAR4"])
        self.assertEqual(nodo.args.args[0].annotation.id, "VAR2")

        acotado = self.normalizar_codigo(
            "def f[T: Base = Predeterminado](dato: T):\n    return dato\n"
        )
        self.assertEqual(acotado.type_params[0].bound.id, "VAR3")
        self.assertEqual(acotado.type_params[0].default_value.id, "VAR4")
