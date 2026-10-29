# Reglas acordadas y plan de implementación

Acuerdo inicial: 27/10/2026. Este documento es la referencia compartida del equipo.
La [consigna oficial](consigna.pdf) prevalece sobre las decisiones técnicas.

## 1. Alcance y decisiones generales

- Buscar similitud estructural entre funciones individuales de archivos Python
  dentro de una carpeta local; alcance de decenas de archivos.
- Python 3.13 como versión de referencia, ya disponible en el entorno inicial.
  Usar la misma versión menor en el equipo para obtener AST comparables.
- Biblioteca estándar: `ast`, `pathlib`, `tokenize`, `copy`, `argparse`, `unittest`
  y utilidades estándar que sean necesarias. Sin dependencias externas.
- CLI exclusivamente. Selección por archivo y nombre; sin entrada de código pegado.
- Extraer todas las `FunctionDef`, incluidos métodos y funciones anidadas.
  No incluir las `AsyncFunctionDef` como objetivos: su soporte es opcional.
- Cuatro módulos: extracción, normalización/serialización, similitud y CLI.
  Las dos operaciones de `normalizador.py` serán funciones separadas.
- Sin base de datos, web, API, interfaz gráfica, IA, caché persistente,
  paralelización ni optimizaciones para miles de archivos.
- Funciones convencionales y estructuras simples. No fijar un límite de líneas.
- Desarrollar una etapa por intervención y revisarla antes de pasar a la siguiente.

## 2. Contratos de los módulos

### Extracción: `extractor.py`

- `extraer_funciones(directorio)` recibe texto o `Path` y devuelve la tupla
  `(funciones, errores)`, con dos listas. Los errores son mensajes de texto;
  el extractor no imprime.
- Cada función será un diccionario con cuatro campos: `nombre` (str), `archivo`
  (str, ruta relativa al directorio con `/`), `linea` (int) y `nodo` (`FunctionDef`).
  No se necesita una clase de datos ni guardar el código fuente completo.
- Buscar `.py` recursivamente y leer con `tokenize.open()` para respetar la
  codificación declarada por Python. Parsear con `ast.parse()`.
- Se puede usar `ast.walk()` para extraer. Ordenar por archivo y línea para no
  depender del orden de exploración del sistema de archivos o de `ast.walk()`.
- No excluir carpetas automáticamente ni ejecutar/importar el código examinado.
- Ante error de sintaxis, codificación o lectura, omitir el archivo, registrar un
  mensaje con su ruta y continuar con los demás. Evitar capturar `Exception` general.
- Una ruta inicial inexistente o que no es directorio lanza `ValueError`;
  no confundirla con una carpeta válida sin funciones, que devuelve listas vacías.
- Conservar los nodos originales: una función externa contiene también el AST
  de sus funciones anidadas; cada anidada es además un resultado independiente.

### Normalización: `normalizador.py`

- `normalizar_funcion(nodo)` recibe un `FunctionDef` y devuelve una copia mediante
  `copy.deepcopy(nodo)` y la clase privada `_Normalizador`, derivada de
  `ast.NodeTransformer`. No altera el original, imprime ni recibe código fuente.
- El nombre de la función raíz será `FUNCION`. Sus metadatos originales se
  conservan en el registro del extractor.
- Usar un solo diccionario de nombres por función analizada. Asignar `VAR1`,
  `VAR2`, etc., a los parámetros en orden sintáctico: posicionales exclusivos,
  normales, `*args`, exclusivos por nombre y `**kwargs`. Registrar todos antes de
  recorrer anotaciones o defaults. Después asignar nuevos nombres en su primera
  aparición durante el recorrido de los campos del AST. La raíz no consume un
  número por su nombre.
- Reutilizar siempre el token asignado al mismo nombre. Aplicar el mapa a
  `Name.id`, `arg.arg`, nombres de definiciones anidadas y clases, alias explícitos
  de imports, nombres de excepciones, `global`/`nonlocal` y nombres capturados por
  patrones. Los nombres de parámetros de tipo, si aparecen, siguen la misma regla.
- Las funciones anidadas dentro del árbol externo usan ese mismo mapa; al
  compararlas como objetivos independientes se inicia un mapa nuevo.
- Registrar también todos los parámetros de definiciones internas y lambdas
  antes de sus anotaciones y defaults. Las definiciones async internas siguen las
  reglas de nombres y docstrings, conservando su tipo; siguen excluidas como
  objetivos del extractor.
- Normalizar también los `Name` usados como llamadas, incluido el nombre propio
  en llamadas recursivas. No resolver si son locales, globales o funciones externas.
- Conservar nombres de atributos, módulos importados y etiquetas de argumentos
  por nombre de las llamadas. Son campos distintos de las referencias `Name`.
- Reemplazar el valor de todos los `Constant` por `LIT`, incluidos números,
  strings, bytes, booleanos y `None`; ignorar el prefijo textual `kind`.
- Eliminar únicamente el docstring inicial de cada función: es documentación,
  no una instrucción que aporte estructura ejecutable. Conservar las demás
  expresiones, operadores, contextos de uso, decoradores, anotaciones y defaults.
- Establecer `type_comment` en `None`. Conservar las posiciones copiadas para
  inspección; ignorarlas en las comparaciones de árboles y la futura serialización.
- Usar visitantes convencionales y un método auxiliar que asigna los nombres.
  Conservar identificadores opcionales ausentes como `None`, sin asignarles token.
- El AST normalizado es una representación para comparar; no se ejecuta ni se
  promete que conserve la semántica del código original.

**Límite elegido para mantener la sencillez:** el mapa es léxico, por nombre,
sin resolver ámbitos ni enlaces entre declaraciones y usos. Un nombre repetido
en ámbitos anidados comparte token. No se garantiza invariancia ante todos los
renombrados con sombreado, cierres, imports o argumentos por nombre. No construir
un analizador semántico para resolver estos casos; registrarlos en el informe.

### Serialización: `normalizador.py`

- `serializar_ast(nodo_normalizado)` devolverá una lista de tokens de texto.
- Recorrer recursivamente en pre-order: emitir el tipo de nodo antes de sus
  campos e hijos. Seguir el orden de `ast.iter_fields()`; no usar `ast.walk()`.
- Emitir marcadores diferenciados para tipos de nodo, nombres de campos, valores,
  inicio/fin de listas y campos ausentes. Conservar también los valores escalares
  relevantes que no son nodos. No incluir posiciones ni comentarios de tipo.
- Los límites deben distinguir, por ejemplo, dos asignaciones en `body` de una
  en `body` y otra en `orelse`. Una lista plana de tipos sin esos límites no alcanza.
- Mantener identificadores normalizados, `LIT`, operadores y estructura. No usar
  texto regenerado ni `ast.dump()` como sustituto del recorrido definido.
- Formato implementado el 28/10/2026: `NODO:tipo`, `CAMPO:nombre`,
  `VALOR:representacion` (con `repr()`), `AUSENTE`, `INICIO_LISTA`, `FIN_LISTA`
  y `FIN_NODO`. Los cierres explícitos conservan los límites de la estructura;
  `repr()` distingue valores escalares de distinto tipo. Es una función recursiva
  con un auxiliar local, sin clases nuevas ni cambios en la normalización.

### Similitud: `similitud.py`

- `crear_ngramas(tokens, n=3)` construirá un conjunto de tuplas consecutivas.
- `calcular_similitud(tokens_a, tokens_b)` aplicará Jaccard: tamaño de la
  intersección dividido por tamaño de la unión. No depende del extractor ni de la CLI.
- Si una secuencia no vacía tiene menos de tres tokens, usar la secuencia completa
  como un único n-grama. Dos secuencias vacías puntúan 1; solo una vacía puntúa 0.
- Elegir inicialmente **n = 3** y **umbral = 0.70**, constantes del programa.
  No agregar opciones de configuración para estos valores.
- El criterio de candidato es `score >= umbral`, usando el score sin redondear.
- En la etapa 4, comprobar estos valores con casos positivos y negativos fijados
  por su significado antes de calcular los scores. Documentar los resultados.
- Si no permiten separar razonablemente esos casos, revisar n o umbral con
  evidencia; no cambiar ejemplos o expectativas para esconder fallos. No agregar
  una segunda métrica automáticamente.
- Jaccard con conjuntos pierde frecuencias y parte del orden global. Un score
  de 1 no demuestra igualdad del AST ni equivalencia semántica.

#### Calibración de la etapa 4 (28/10/2026)

Los pares y sus expectativas se fijaron en `ejemplos/funciones.py` antes de
calcular los scores. Los archivos se leen con el extractor, sin importarlos ni
ejecutarlos. Se usan las funciones de normalización y serialización vigentes.

| Caso | Par | Intersección / unión | Score con n = 3 |
| --- | --- | --- | --- |
| Positivo aritmético | `sumar` / `total` | 80 / 80 | 1.00000000 |
| Positivo con control de flujo | `acumular` / `contar` | 109 / 109 | 1.00000000 |
| Negativo: aritmética / recorrido con condicional | `sumar` / `contar` | 68 / 121 | 0.56198347 |
| Negativo: retorno / bucle con acumulación | `identidad` / `acumular` | 48 / 111 | 0.43243243 |
| Exploratorio: instrucciones independientes reordenadas | `operaciones` / `operaciones_reordenadas` | 92 / 92 | 1.00000000 |

Se mantienen n = 3 y umbral = 0.70: los trigramas conservan vecindad local de
tokens con una implementación simple y separan estos positivos y negativos.
El umbral queda por encima del mayor negativo (0.56198347) y por debajo de los
positivos. Esta calibración pequeña no demuestra precisión general ni que sea
el mejor n posible; no se ensayaron otros valores al pasar los casos acordados.
Los marcadores estructurales compartidos también contribuyen al score.

El reordenamiento exploratorio conserva el conjunto de trigramas y puntúa 1,
aunque las listas de tokens son distintas. Esto muestra la pérdida de orden
global y frecuencias de Jaccard con conjuntos; no promete detectar cualquier
reordenamiento ni equivalencia de comportamiento.

`similitud.py` contiene solo las constantes y dos funciones convencionales.
`crear_ngramas()` rechaza n menor que 1 con `ValueError`; no se agregaron
configuraciones de consola ni dependencias.

### Búsqueda y consola: `buscar_similares.py`

- Interfaz: `--dir DIRECTORIO --funcion archivo.py:nombre --top K`.
  `--top` tendrá valor predeterminado 5 y aceptará solo enteros positivos.
- El archivo objetivo es relativo a `--dir`, incluidos subdirectorios. Separar
  archivo y nombre por el último `:`. No aceptar una ruta objetivo fuera de la raíz.
- Agregar `--linea NUMERO` opcional para resolver nombres repetidos. Sin una
  selección única, mostrar coincidencias y líneas; nunca elegir arbitrariamente.
- Extraer una vez y normalizar/serializar cada función una vez por ejecución.
  Comparar solo el objetivo con las demás; no hace falta todos contra todos.
- Identificar funciones por archivo y línea. Excluir únicamente el objetivo;
  incluir otras funciones idénticas aunque compartan nombre.
- Ordenar por score descendente y, en empates, por archivo y línea ascendentes.
- Mostrar hasta K resultados con archivo, nombre, línea, score con cuatro
  decimales e indicación de candidato a duplicado. El umbral marca, no filtra el top-K.
- Una carpeta sin funciones y un objetivo sin otros candidatos tendrán mensajes
  claros. Si no hay otras funciones, devolver cero resultados sin inventarlos.
- Mostrar errores de entrada y avisos de archivos omitidos por stderr. Errores
  de entrada terminan con código distinto de cero; una búsqueda válida sin otros
  candidatos termina correctamente.
- Separar la coordinación de búsqueda de la impresión para poder probarla.

## 3. Pruebas y criterios comunes

- Usar `unittest`, archivos temporales y casos pequeños. Sin frameworks externos.
- Comando desde la raíz: `python -m unittest discover -s tests -v`.
- Los dos positivos obligatorios serán pares de clones con renombrado de variables
  y parámetros: un caso aritmético y otro con control de flujo. Deben producir
  representaciones iguales y score 1. Cambiar también sus nombres de función.
- Los dos negativos obligatorios serán pares claramente distintos: cálculo
  aritmético frente a recorrido con condicional, y retorno simple frente a un
  bucle con acumulación. Deben quedar por debajo del umbral elegido al calibrar.
- Probar además literales, correspondencia (`a+b` frente a `a+a`), operadores,
  recursión renombrada, límites de bloques y preservación del AST original.
- Una operación distinta debe cambiar los tokens; no se exige que un único
  operador distinto baje necesariamente el score por debajo del umbral.
- Evaluar un reordenamiento de instrucciones independientes como caso exploratorio.
  No prometer que todos los reordenamientos sean detectados ni que sean equivalentes.
- Cada etapa incorpora pruebas de su responsabilidad. La etapa 6 comprueba su
  integración y completa lo necesario, sin postergar todas las pruebas hasta allí.

## 4. Etapas y condiciones de cierre

Las etapas 0 a 6 están completadas. La suite completa pasa en Python 3.13.15.
El trabajo pendiente corresponde a la etapa 7: entrega y defensa.
El esfuerzo relativo es una
orientación; la normalización concentra la mayor incertidumbre. No es una agenda
ni un compromiso de horas. Al cerrar cada etapa se actualiza esta lista y se
explica el funcionamiento al equipo antes de avanzar.

- [x] **Etapa 0. Preparación y acuerdos** — esfuerzo bajo.
  Incorporar consigna local, README, AGENTS y este plan. No crear módulos vacíos.
  Cierre: requisitos, decisiones, límites y orden de trabajo disponibles en el
  repositorio local; el commit queda sujeto a indicación del equipo.

- [x] **Etapa 1. Extracción** — esfuerzo medio.
  Crear `extractor.py` y `tests/test_extractor.py`.
  Probar funciones simples y múltiples, subdirectorios, métodos, anidadas,
  metadatos y orden, exclusión de async como objetivo, errores de sintaxis y lectura.
  Cierre: devuelve registros completos y avisos sin detener el resto del análisis;
  pruebas del extractor aprobadas.

- [x] **Etapa 2. Normalización** — esfuerzo mayor.
  Crear `normalizador.py` y `tests/test_normalizador.py`, inicialmente sin serializador.
  Probar el contrato de nombres y literales, docstrings, operadores, recursión,
  anidadas, reinicio del mapa e inmutabilidad del original. Usar `ast.dump()` solo
  para inspección y comparación de árboles en estas pruebas.
  Cierre: los renombrados soportados producen AST equivalentes y las diferencias
  de correspondencia y operadores permanecen; límites explícitos y pruebas aprobadas.

- [x] **Etapa 3. Serialización** — esfuerzo medio.
  Agregar el recorrido a `normalizador.py` y ampliar sus pruebas.
  Cierre: tokens deterministas en pre-order, sin nombres propios ni posiciones;
  diferenciar bloques `body`/`orelse`, valores ausentes y listas vacías.

- [x] **Etapa 4. Métrica y umbral** — esfuerzo medio.
  Crear `similitud.py`, `tests/test_similitud.py` y los casos de `ejemplos/`.
  Probar fórmula, identidad, simetría, rango y secuencias cortas/vacías. Medir los
  dos positivos, dos negativos y reordenamiento exploratorio. Registrar scores y
  justificación de n y umbral en este documento antes del informe final.
  Cierre: casos obligatorios aprobados, valores justificados y limitaciones conocidas.

- [x] **Etapa 5. Buscador y CLI** — esfuerzo medio.
  Crear `buscar_similares.py` y `tests/test_buscador.py`.
  Cierre: búsqueda por archivo/nombre/línea, top-K, exclusión del objetivo, empates,
  etiquetas por umbral y errores básicos verificados; primer ejemplo ejecutable
  documentado con sus nombres de archivo reales.

- [x] **Etapa 6. Integración y revisión** — esfuerzo medio.
  Ejecutar la suite completa y la CLI sobre ejemplos y otra carpeta pequeña.
  Probar mezcla de archivos válidos/inválidos, ausencia y ambigüedad del objetivo,
  K inválido o mayor que los candidatos, sin candidatos y rutas con espacios.
  Cierre: flujo completo verificado contra todos los requisitos de la consigna;
  corregir errores sin añadir características ni optimizaciones innecesarias.
  Revisión y cierre realizados el 29/10/2026: 64 pruebas aprobadas en
  Python 3.13.15, incluidas las 11 de integración; correcciones verificadas.

- [ ] **Etapa 7. Entrega y defensa** — esfuerzo medio.
  Completar README e `informe.pdf` de hasta dos páginas: decisiones, métrica y su
  justificación, n, umbral, limitaciones y posibles mejoras. Preparar demostración
  con positivos/negativos y preguntas para explicar o modificar cada módulo.
  Cierre: suite aprobada, instrucciones reproducibles y entregables presentes en
  el repositorio; comprobar historial incremental y acceso de docentes si es privado.
  La publicación queda a cargo del equipo, con indicación expresa para push.

## 5. Trazabilidad mínima de la entrega

| Requisito | Etapas responsables |
| --- | --- |
| Directorios, `ast.parse()`, todas las `FunctionDef` y metadatos | 1, 6 |
| Variables/parámetros, literales y nombre propio normalizados | 2, 6 |
| Tokens de tipos y valores normalizados en pre-order | 3, 6 |
| Métrica permitida, n justificado y umbral documentado | 4, 7 |
| Objetivo, top-K configurable, scores y CLI | 5, 6 |
| Al menos dos positivos y dos negativos | 4, 6 |
| Código modular, informe de hasta dos páginas y commits incrementales | Todas; cierre en 7 |

## 6. Fuentes y seguimiento

- [Consigna oficial](consigna.pdf), secciones 3 a 6.
- [Documentación oficial de AST](https://docs.python.org/3.13/library/ast.html).
- Material de la cátedra cuando esté disponible. No recurrir a implementaciones
  de terceros ni iniciar otra investigación externa por cambiar de chat.

Etapas 0, 1 y 2 completadas. `extractor.py` conserva su función directa con
diccionarios. `normalizador.py` incorpora una función pública y una clase privada
con visitantes explícitos. Se aprobaron las 27 pruebas (11 del extractor y 16 del
normalizador) el 27/10/2026 con Python 3.13.13. Comando ejecutado:
`python -B -m unittest discover -s tests -v` (`-B` evita generar archivos de caché).
Las nuevas pruebas cubren clones aritméticos y con control de flujo, diferencias
de correspondencia y operadores, categorías de parámetros, reinicio del mapa,
copia y posiciones originales, definiciones internas, recursión, constantes,
docstrings, comentarios de tipo y otros identificadores acordados. La limitación
del mapa compartido ante sombreado está comprobada y documentada. No se cambió
el extractor ni se implementaron etapas posteriores.

Etapa 3 implementada el 28/10/2026. Se agregó `serializar_ast()` y cinco pruebas
de pre-order, límites de bloques, ausentes/listas vacías, determinismo,
inmutabilidad, exclusión de posiciones/comentarios y valores escalares. También
se ampliaron las pruebas existentes de clones y diferencias de operadores y
correspondencias para comparar tokens.

Se ejecutó `python -B -m unittest discover -s tests -v` con Python 3.12.14,
disponible en esta sesión: 32 pruebas, 31 aprobadas y 1 error. Todas las pruebas
nuevas y ampliadas pasaron. El error existente corresponde a sintaxis de
parámetros de tipo con defaults, que requiere Python 3.13. Queda pendiente
repetir la suite completa con Python 3.13; no se cambió esa prueba ni la versión
de referencia para ocultar la diferencia de entorno.

Etapa 4 implementada el 28/10/2026: `similitud.py`, `tests/test_similitud.py` y
`ejemplos/funciones.py`. Se aprobaron las 11 pruebas nuevas de n-gramas,
Jaccard y calibración con `python -B -m unittest discover -s tests -p
test_similitud.py -v`. La suite completa ejecutada con Python 3.12.14 tiene
43 pruebas: 42 aprobadas y el mismo error existente de sintaxis que requiere
Python 3.13. Sigue pendiente repetir la suite con la versión de referencia.
Los scores medidos y la justificación de n y umbral están en la sección 2.

Etapa 5 completada el 28/10/2026. Se creó `buscar_similares.py` con `buscar()`
y `main()` separadas para permitir pruebas independientes de la CLI. Se creó
`tests/test_buscador.py` con 10 pruebas: 2 positivos obligatorios (clones
aritmético y con control de flujo), 2 negativos obligatorios (aritmética vs.
bucle y retorno simple vs. acumulador), exclusión del objetivo, top-K, nombre
ambiguó, sin candidatos y directorio inválido. Las 10 pruebas aprobaron.

Ejemplo ejecutable verificado desde la raíz del proyecto:
  python buscar_similares.py --dir ./ejemplos --funcion funciones.py:sumar --top 5

Salida obtenida:
  1. funciones.py:total (línea 15) — score: 1.0000 [CANDIDATO A DUPLICADO]
  2. funciones.py:operaciones (línea 40) — score: 0.7030 [CANDIDATO A DUPLICADO]
  3. funciones.py:operaciones_reordenadas (línea 46) — score: 0.7030 [CANDIDATO A DUPLICADO]
  4. funciones.py:identidad (línea 36) — score: 0.5854
  5. funciones.py:acumular (línea 20) — score: 0.5620

Revisión de la etapa 6 realizada el 29/10/2026 por indicación del equipo.
Se agregó `tests/test_integracion.py`, que ejecuta la CLI con el intérprete
actual en procesos reales, desde una carpeta temporal diferente al repositorio.
Se verificó el ejemplo de `ejemplos/` y otra carpeta pequeña con subcarpetas,
rutas con espacios, empates por archivo/línea, K inválido o mayor a la cantidad
disponible, selección ambigua y por línea, objetivo ausente, carpeta vacía,
sin otros candidatos y mezcla de sintaxis/codificaciones válidas e inválidas.
Un archivo de prueba contiene un `raise RuntimeError` al nivel del módulo:
la búsqueda funciona porque solo lee y parsea el archivo, sin ejecutarlo.

Las pruebas demostraron problemas que se corrigieron en `buscar_similares.py`:

- Normalizar con `Path` la ruta objetivo a una ruta relativa con `/` para
  admitir separadores de Windows. Rechazar explícitamente rutas absolutas o
  resueltas fuera de la raíz, de acuerdo con el contrato existente.
- Validar top-K también en `buscar()`, evitando recortes silenciosos con 0 o -1.
- Distinguir una carpeta sin funciones con un mensaje específico.
- Conservar los avisos de archivos omitidos cuando falla la selección del
  objetivo. Un auxiliar local construye el `ValueError` con esos avisos para
  que `main()` los muestre por stderr, sin repetir la extracción.

Se ejecutó `python -X utf8 -B -m unittest discover -s tests -v`: 64 pruebas,
63 aprobadas y 1 error existente por sintaxis de Python 3.13, usando Python
3.12.14. Las 11 pruebas de integración y las 10 del buscador pasaron. También
se ejecutó `python -X utf8 -B buscar_similares.py --dir ./ejemplos --funcion
funciones.py:sumar --top 5`, con el mismo ranking documentado en la etapa 5.
Se actualizó el README para reflejar la CLI disponible y los resultados reales.

Al comenzar no se encontró un intérprete Python 3.13 disponible en las
ubicaciones revisadas. Posteriormente, con autorización del equipo, se instaló
Python 3.13.15 para el usuario mediante el paquete `Python.Python.3.13` de
winget, cuyo instalador proviene de python.org. Se ejecutó
`C:\Users\nicog\AppData\Local\Programs\Python\Python313\python.exe` con
`-X utf8 -B -m unittest discover -s tests -v`: las 64 pruebas pasaron en
21.604 segundos, sin errores ni omisiones. No se modificó la prueba que
requiere 3.13. Se cierra la etapa 6. La etapa 7 continúa abierta.
No se realizaron commits ni publicaciones durante esta revisión.

Todo cambio posterior de una regla debe indicar motivo, prueba que lo sustenta
y fecha. Los únicos valores a calibrar son n y umbral; el resto constituye la
base acordada, salvo que se encuentre una contradicción con la consigna o un error.

Borrador del informe preparado el 29/10/2026 en `output/pdf/informe.pdf`.
Tiene dos páginas A4 e incluye decisiones, métrica, scores de los casos fijados,
limitaciones y mejoras futuras. La etapa 7 no se cierra: queda pendiente la
revisión del equipo, la preparación de la defensa y completar la entrega.
