# Guía de trabajo

## Referencias y prioridades

- Leer `docs/consigna.pdf` y `docs/PLAN.md` antes de cambiar el proyecto.
- `docs/PLAN.md` concentra las decisiones acordadas y la etapa vigente para todos
  los colaboradores. No usar el prompt original como una orden de implementar
  etapas completas automáticamente.
- Priorizar cumplimiento de la consigna, corrección, claridad y simplicidad.
  La cantidad de líneas es orientativa, nunca un objetivo ni un límite.
- Cada integrante debe poder explicar y modificar cualquier parte del código.

## Método y fuentes

- Al iniciar un proyecto o chat de desarrollo, aplicar la skill personal
  `investigar-soluciones`. Reutilizar el análisis vigente en continuaciones.
- Fuentes permitidas: consigna, recursos que recomienda, material de la cátedra y
  documentación oficial de la biblioteca estándar de Python.
- No buscar implementaciones de terceros, copiar código externo ni agregar
  dependencias sin una indicación expresa. La investigación no autoriza ampliar
  el alcance.

## Implementación

- Python 3.13 como versión de referencia; biblioteca estándar y `unittest`.
- Mantener los cuatro módulos definidos en el plan y sus responsabilidades.
- Preferir funciones convencionales, nombres descriptivos y estructuras simples.
  No introducir clases salvo utilidad concreta; la subclase de `NodeTransformer`
  está prevista para normalizar.
- Comentarios y explicaciones en español cuando aporten comprensión. Evitar
  código comprimido, comentarios obvios y abstracciones innecesarias.
- No agregar funcionalidades opcionales, optimizaciones, configuraciones,
  refactorizaciones generales ni módulos vacíos por anticipado.
- No importar ni ejecutar los archivos analizados: leerlos y usar `ast.parse()`.

## Trabajo por etapas

1. Revisar el estado del repositorio y localizar la etapa en `docs/PLAN.md`.
2. Explicar brevemente el alcance de la etapa solicitada.
3. Implementar únicamente esa etapa y sus pruebas útiles.
4. Ejecutar las pruebas disponibles, corregir fallos e informar lo no verificado.
5. Actualizar el estado del plan y el README según lo realmente implementado.
6. Explicar archivos, funciones, algoritmo, decisiones, pruebas y limitaciones.
7. Detenerse: avanzar de etapa requiere indicación del usuario.

Las decisiones ya acordadas no necesitan una nueva aprobación. Si una prueba
demuestra que una decisión debe cambiar, explicar la evidencia y la alternativa
mínima antes de introducir una dirección nueva.

## Documentación y Git

- Registrar cambios de decisiones y su motivo en `docs/PLAN.md`, sin duplicar toda
  la especificación en el README ni en este archivo.
- No presentar funciones previstas como terminadas ni afirmar pruebas no ejecutadas.
- Sugerir commits por avances reales. No crear commits, remotos ni hacer push sin
  indicación expresa; no fabricar un historial retrospectivo.
