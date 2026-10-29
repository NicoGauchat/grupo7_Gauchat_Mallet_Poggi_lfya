# Motor de búsqueda de funciones similares vía AST

Trabajo Práctico Final 2026 de Lenguajes Formales y Autómatas, UCSE.
Grupo 7: Gauchat, Mallet y Poggi.

## Objetivo

Buscar funciones estructuralmente similares dentro de una carpeta de archivos
Python. El proceso previsto es extraer funciones, normalizar sus árboles de
sintaxis abstracta (AST), serializarlos en pre-order y comparar sus tokens con
Jaccard sobre n-gramas.

La prioridad es cumplir la consigna con código correcto, sencillo y comprensible
para que cada integrante pueda explicar y modificar cualquier módulo.

## Estado actual

Etapas 0 a 6 completadas: decisiones documentadas, extractor,
normalización, serialización, similitud y buscador por consola. El extractor devuelve funciones con
sus metadatos y AST; el normalizador transforma una copia, el serializador
produce tokens y la métrica calcula Jaccard sobre trigramas.

La integración se revisó con pruebas de la consola en procesos reales y se
corrigieron los casos encontrados. Las 64 pruebas pasan en Python 3.13.15.
Hay un borrador del informe en `output/pdf/informe.pdf`, pendiente de revisión
del equipo. La preparación de la defensa y el cierre de la entrega siguen pendientes.

## Documentación compartida

- [Consigna oficial](docs/consigna.pdf): requisitos de la cátedra.
- [Reglas acordadas y plan por etapas](docs/PLAN.md): referencia técnica para todos
  los colaboradores, con contratos y criterios de aceptación.
- [AGENTS.md](AGENTS.md): instrucciones de trabajo para asistentes.

La consigna tiene prioridad. Las decisiones están concentradas en el plan para
evitar mantener versiones distintas en varios documentos.

## Organización prevista

| Archivo | Responsabilidad |
| --- | --- |
| `extractor.py` | Recorrer archivos y extraer funciones con sus metadatos y AST |
| `normalizador.py` | Normalizar una copia del AST y serializarla con funciones separadas |
| `similitud.py` | Construir n-gramas y calcular Jaccard |
| `buscar_similares.py` | Resolver argumentos, coordinar la búsqueda y mostrar resultados |
| `tests/` | Pruebas unitarias y de integración con `unittest` |
| `ejemplos/` | Casos pequeños para comprobar y defender el programa |
| `output/pdf/informe.pdf` | Borrador del informe de hasta dos páginas |

Estos archivos se incorporarán cuando corresponda su etapa, sin crear módulos vacíos.

## Entorno y uso

Versión de referencia: Python 3.13, disponible en el entorno inicial. Se usará
únicamente la biblioteca estándar, sin instalaciones adicionales.

### Extractor disponible

Desde Python, con la raíz del proyecto como directorio de trabajo:

```python
from extractor import extraer_funciones

funciones, errores = extraer_funciones("./carpeta_a_analizar")
for funcion in funciones:
    print(funcion["archivo"], funcion["nombre"], funcion["linea"])
for error in errores:
    print(error)
```

La carpeta indicada debe existir. Cada registro incluye `nombre`, `archivo`
(ruta relativa con `/`), `linea` y `nodo` (el AST original de la función).
El extractor devuelve los errores sin imprimirlos y lanza `ValueError` si la
entrada no es un directorio existente. Solo lee y parsea el código: no lo ejecuta.

### Normalización disponible

Sobre los registros del ejemplo anterior:

```python
import ast
from normalizador import normalizar_funcion

for funcion in funciones:
    normalizado = normalizar_funcion(funcion["nodo"])
    print(funcion["nombre"], ast.dump(normalizado, indent=2))
```

`normalizar_funcion(nodo)` devuelve un AST nuevo: el original conserva sus nombres,
literales y posiciones. El nombre raíz pasa a `FUNCION`, los identificadores a
`VAR1`, `VAR2`, etc., y las constantes a `LIT`. Se eliminan docstrings iniciales de
funciones y comentarios de tipo; se conservan operadores y estructura.

Primero se registran los parámetros en orden sintáctico; después, los nombres
nuevos según el recorrido. Cada llamada inicia un mapa independiente. Las
funciones anidadas usan el mismo mapa mientras se recorre el árbol externo.

El mapa es léxico: no distingue ámbitos ni resuelve referencias semánticas. Se
conservan nombres de atributos, módulos importados y etiquetas de argumentos en
llamadas. No se garantiza detectar todos sus renombrados, ni los de variables
con sombreado. El árbol normalizado sirve para comparar; no se ejecuta ni se
promete que preserve el comportamiento original.

### Serialización disponible

Después de normalizar una función:

```python
from normalizador import serializar_ast

tokens = serializar_ast(normalizado)
print(tokens)
```

El recorrido recursivo en pre-order emite primero el tipo de nodo y después sus
campos e hijos en el orden de `ast.iter_fields()`. Usa `NODO:tipo`, `CAMPO:nombre`,
`VALOR:representacion`, `AUSENTE`, `INICIO_LISTA`, `FIN_LISTA` y `FIN_NODO`.
Estos límites permiten distinguir bloques, listas vacías y campos sin valor.
Los valores usan `repr()` para distinguir, por ejemplo, el número `1` del texto
`'1'`. No se incluyen posiciones ni comentarios de tipo, ni se modifica el AST.
La función recibe un árbol ya normalizado; no realiza la normalización por sí sola.

### Similitud disponible

```python
from similitud import calcular_similitud, UMBRAL_SIMILITUD

score = calcular_similitud(tokens_a, tokens_b)
print(score)
print(score >= UMBRAL_SIMILITUD)
```

`tokens_a` y `tokens_b` son las listas de dos funciones ya normalizadas y
serializadas. La métrica divide la cantidad de trigramas compartidos por la
cantidad de trigramas distintos entre ambas. Dos secuencias vacías puntúan 1;
solo una vacía puntúa 0. Una secuencia no vacía menor a tres tokens forma un
único n-grama. `crear_ngramas(tokens, n=3)` también está disponible por separado.

Se mantienen n = 3 y umbral = 0.70 después de comprobar dos pares positivos
y dos negativos en `ejemplos/funciones.py`. La calibración y sus scores están
en el plan. Los conjuntos pierden frecuencias y parte del orden: el ejemplo de
instrucciones reordenadas puntúa 1 aunque sus tokens difieren. Un score de 1
no demuestra igualdad de árboles ni equivalencia de comportamiento.

### Buscador por consola

Desde la raíz del proyecto:

```bash
python -B buscar_similares.py --dir ./ejemplos --funcion funciones.py:sumar --top 5
```

El archivo objetivo debe ser relativo a `--dir`. Si el nombre se repite dentro
del archivo, agregar `--linea NUMERO`. Se muestran archivo, nombre, línea,
score con cuatro decimales y la indicación de candidato a duplicado.
El umbral etiqueta los resultados, sin excluir los de score menor a 0.70.
`--top` vale 5 por defecto y acepta únicamente enteros positivos.

Las rutas con espacios se escriben entre comillas. Se aceptan los separadores
de rutas del sistema y se rechazan rutas absolutas o que salgan de la raíz.
Los archivos inválidos generan avisos por stderr; los errores de entrada
terminan con código distinto de cero. Una búsqueda válida sin otras funciones
termina correctamente con un mensaje, sin inventar resultados.

En el ejemplo, `total` aparece primero con score 1.0000. `operaciones` y
`operaciones_reordenadas` puntúan 0.7030: también se marcan como candidatas.
La etiqueta indica similitud estructural aproximada, no igualdad de funciones.

### Pruebas

Las pruebas se ejecutan desde la raíz con:

```bash
python -m unittest discover -s tests -v
```

Actualmente hay 64 pruebas: 11 del extractor, 21 de normalización/serialización,
11 de similitud/calibración, 10 del buscador y 11 de integración. Las primeras
usan carpetas temporales y simulan el error de lectura para no depender de
permisos del sistema operativo. Las de normalización usan árboles en memoria y
comprueban equivalencias, diferencias relevantes y conservación de los originales.

Verificación del 29/10/2026 en Python 3.13.15: las 64 pruebas aprobadas, sin
errores ni omisiones. Se ejecutó el intérprete instalado en
`C:\Users\nicog\AppData\Local\Programs\Python\Python313\python.exe` con
`-X utf8 -B -m unittest discover -s tests -v`. En PowerShell:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe" -X utf8 -B -m unittest discover -s tests -v
```

`-X utf8` fija la codificación de la salida y `-B` evita generar archivos de
caché. La prueba que fallaba con Python 3.12 por sintaxis de parámetros de tipo
con defaults pasa con la versión de referencia, sin modificarla.

La integración cubre subcarpetas, rutas con espacios, separadores de Windows,
empates, top-K mayor a los candidatos e inválido, nombres ambiguos y selección
por línea, carpeta vacía, objetivo ausente, ausencia de otros candidatos y
mezcla de archivos válidos e inválidos. También comprueba que el código
analizado no se ejecute y que los avisos no se pierdan al fallar la selección.

## Límites del alcance

Comparación estructural de funciones síncronas en decenas de archivos locales.
No demuestra equivalencia de comportamiento ni detecta todos los tipos de clones.
No incluye interfaz gráfica, servicios externos, base de datos ni comparación
semántica. Los límites precisos de normalización y similitud están en el plan.

Entrega: 30/10/2026 a las 23:59. Defensa oral individual: 04/11/2026.
