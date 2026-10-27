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

Etapas 0, 1 y 2 completadas: decisiones documentadas, extractor y normalización
implementados, con 27 pruebas automatizadas aprobadas. El extractor devuelve
funciones con sus metadatos y AST; el normalizador transforma una copia del árbol.

Serialización, similitud y CLI siguen pendientes. La próxima etapa es la
serialización, que se iniciará únicamente cuando el equipo lo indique.

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
| `informe.pdf` | Informe final de hasta dos páginas |

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

### CLI prevista

Cuando esté completada la etapa 5, desde la raíz del proyecto:

```bash
python buscar_similares.py --dir ./ejemplos --funcion archivo1.py:sumar --top 5
```

El archivo objetivo será relativo a `--dir`. Si el nombre se repite dentro del
archivo, se podrá agregar `--linea NUMERO`. Se mostrarán archivo, nombre, línea,
score y la indicación de candidato a duplicado.

### Pruebas

Las pruebas se ejecutan desde la raíz con:

```bash
python -m unittest discover -s tests -v
```

Actualmente hay 27 pruebas: 11 del extractor y 16 de normalización. Las primeras
usan carpetas temporales y simulan el error de lectura para no depender de
permisos del sistema operativo. Las de normalización usan árboles en memoria y
comprueban equivalencias, diferencias relevantes y conservación de los originales.

## Límites del alcance

Comparación estructural de funciones síncronas en decenas de archivos locales.
No demuestra equivalencia de comportamiento ni detecta todos los tipos de clones.
No incluye interfaz gráfica, servicios externos, base de datos ni comparación
semántica. Los límites precisos de normalización y similitud están en el plan.

Entrega: 30/10/2026 a las 23:59. Defensa oral individual: 04/11/2026.
