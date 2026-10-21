---
tipo: bitacora-clase
curso: Inteligencia Artificial Generativa y Sistemas Inteligentes
periodo: EAM-2026II
equipo: SosaJoan-MejiaAlejandra
corte: 2
semana: "4"
clase: 6
fecha: 2026-09-30
estado: en-progreso
tags:
  - ai
  - bitacora
---

# Bitácora — Clase 6

## 1. Datos de la sesión

| Campo | Registro |
|---|---|
| Tema | Embeddings y búsqueda semántica |
| Objetivo | Explicar cómo se representan textos mediante embeddings, recuperar pasajes pertinentes para una consulta y reconocer cuándo los resultados aún no permiten responder. |
| Proyecto | Buscador de conocimiento: recuperar contenido por significado y entregar resultados pertinentes con referencia al documento de origen. |
| Inicio | 6:00pm |
| Cierre | 9:00pm |

## 2. Participación y responsabilidades

| Integrante | Asistió | Rol de la clase | Responsabilidad asumida | Aporte verificable |
| --- | :---: | --- | --- | --- |
| Joan Sebastián Sosa Bedoya | Sí | Integrante del equipo | Ejecutar el notebook y registrar los resultados de la búsqueda. | Capturas de la ejecución y tabla de resultados. |
| Alejandra Mejía Patiño | Sí | Integrante del equipo | Adaptar el corpus del proyecto, diseñar las pruebas y documentar fallos. | Corpus de nueve pasajes con documento, código y sección; batería de cinco pruebas. |

## 3. Reto aplicado al proyecto

### Funcionalidad trabajada

Primera búsqueda semántica comprobable del Buscador de conocimiento sobre **el corpus del proyecto**. Se reemplazó el corpus de demostración (contraseña, error 403, SOL-1001) por nueve pasajes de las políticas del repositorio documental ficticio de la Clase 04:

- `Politica_Recursos_Humanos.pdf` (**DOC-1001**, vigente): Vacaciones (RH-1 a RH-3), Incapacidades (RH-4) y Vigencia del documento (RH-5).
- `Politica_Permisos.pdf` (**DOC-1002**, en revisión): Permisos laborales (PER-1 y PER-2), Trabajo remoto (PER-3) y Vigencia del documento (PER-4).
- `Manual_Induccion` (DOC-1003) quedó **excluido** por estar desactualizado.

Cada pasaje se convirtió en un vector con un modelo de embeddings. Las consultas se codificaron con el mismo modelo y se recuperaron los pasajes más cercanos por similitud coseno. Cada resultado muestra su **documento de origen, código y sección**, además del puntaje y el texto. Se contrastó con la búsqueda literal y se probaron consultas fuera de cobertura. Todavía no se generan respuestas con los pasajes; eso corresponde a la Clase 08.

### Criterios de aceptación

- [x] Sustituir el corpus de demostración por pasajes del proyecto, con documento de origen, código y sección.
- [x] Convertir el corpus en embeddings y mostrar la forma de la matriz (9 × 384).
- [x] Recibir una consulta nueva, calcular su embedding y mostrar el ranking con identificador, documento de origen, texto y puntaje.
- [x] Comparar la búsqueda semántica con la búsqueda literal (`casa`, `DOC-1002`, `préstamo`).
- [x] Probar una paráfrasis, una condición con su consecuencia, una excepción, un dato actual que el corpus no contiene (vigencia) y una pregunta fuera de cobertura.
- [x] Leer los pasajes recuperados antes de decidir si responden la pregunta.

### Archivos o componentes modificados

- `Busqueda_Semantica_proyecto.ipynb`:
    - Encabezado con el proyecto, los integrantes y el objetivo.
    - El corpus de cinco pasajes genéricos se cambió por nueve pasajes de DOC-1001 y DOC-1002, con los campos `id`, `documento`, `codigo`, `seccion` y `texto`.
    - La función `mostrar()` imprime el documento de origen de cada resultado.
    - La búsqueda literal usa `casa` (la política dice «trabajo remoto»).
    - La consulta principal es «Quiero trabajar desde casa un par de días, ¿qué necesito?».
    - La batería de la sección 8 tiene cinco pruebas del proyecto y un veredicto automático de puesto.
    - El contraste literal usa `DOC-1002` y `préstamo`.
    - Las preguntas de cierre se adaptaron al corpus.

## 4. Decisiones técnicas

| Decisión | Razón | Alternativa descartada |
|---|---|---|
| Corpus de nueve pasajes de DOC-1001 y DOC-1002, un pasaje por párrafo | Son los mismos documentos que se usan en las clases 04, 07 y 08, así que el proyecto conserva un solo corpus de principio a fin. | Mantener el corpus genérico del campus virtual, que no corresponde al proyecto. |
| Guardar `documento`, `codigo` y `seccion` en cada pasaje | El objetivo del proyecto exige entregar la referencia al documento de origen. | Guardar solo un identificador (`P1`…`P5`) sin procedencia. |
| Excluir `Manual_Induccion` (DOC-1003) | Su estado es desactualizado; recuperar texto de él daría información no válida. | Incluir todos los documentos del repositorio. |
| Modelo `paraphrase-multilingual-MiniLM-L12-v2` | Es multilingüe, funciona sin clave de API ni GPU, sirve para consultas en español y es el mismo de las clases 07 y 08. | Usar el modelo generativo para adivinar el pasaje más parecido. |
| Similitud coseno con vectores normalizados (producto punto) | Mantiene fijos el modelo, el preprocesamiento y la medida, para saber qué se evalúa cuando cambia un resultado. | Producto punto sin normalizar, cuyo orden puede cambiar. |
| `K = 3` | Permite ver los tres candidatos más cercanos y comparar sus puntajes. | Mostrar un solo resultado. |
| Calcular los vectores del corpus una sola vez, antes de recibir la consulta | Evita recalcular y separa la preparación del corpus de la consulta. | Recodificar el corpus en cada búsqueda. |
| No fijar un umbral automático de similitud | Con nueve pasajes, un umbral podría fallar con otras preguntas o con el corpus completo de la Clase 07. | Descartar resultados por debajo de un puntaje fijo. |

## 5. Problemas y soluciones

| Problema encontrado | Causa identificada | Solución aplicada | ¿Cómo se verificó? |
| --- | --- | --- | --- |
| Para «¿Cómo solicito un préstamo de nómina?» el buscador devolvió tres candidatos (____ · ____, ____ · ____) aunque ninguno trata el tema. | Siempre existe un «más cercano» dentro del corpus, aunque ninguno resuelva la pregunta. | Leer los textos recuperados y concluir que el corpus no tiene cobertura; no usarlos como respuesta. | La búsqueda literal de `préstamo` devolvió `[]` y se leyeron los pasajes recuperados. |
| Para «¿Está vigente el documento DOC-1002?» apareció PER-4 en el puesto ____ (____), pero ese pasaje no contiene el estado. | PER-4 solo dice que el documento se identifica con DOC-1002 y que su vigencia se consulta en el repositorio. El estado actual no está en el texto. | No responder la vigencia a partir de PER-4. Ese dato lo da la herramienta `consultar_estado_documento` de la Clase 04. | La búsqueda literal de `DOC-1002` devolvió solo PER-4 y se leyó su texto. |
| *(Completar si ocurre: una prueba con margen pequeño entre el primero y el segundo, o una prueba que falló.)* | | | Se compararon los puntajes de la sección 8. |

### Resultados de la batería de pruebas (corpus del proyecto, `K = 3`)

| Consulta | Esperado | Primer resultado | Segundo | Lectura |
|---|---|---|---|---|
| ¿Con cuánto tiempo debo pedir mis vacaciones? | RH-1 (DOC-1001 · Vacaciones) | | | Paráfrasis: no dice «quince días hábiles». |
| ¿Me aprueban las vacaciones si las pido con menos de quince días? | RH-2 (DOC-1001 · Vacaciones) | | | Condición y consecuencia en el mismo pasaje. |
| Tuve una calamidad, ¿puedo pedir el permiso hoy mismo? | PER-2 (DOC-1002 · Permisos laborales) | | | Excepción a la regla de dos días de anticipación. |
| ¿Está vigente el documento DOC-1002? | Ninguno suficiente | | | PER-4 contiene el código, no el estado. |
| ¿Cómo solicito un préstamo de nómina? | Ninguno suficiente | | | Fuera de cobertura. |

Consulta principal de la demo («Quiero trabajar desde casa un par de días, ¿qué necesito?»): esperado PER-3 (DOC-1002 · Trabajo remoto). Obtenido: ____ · ____, ____ · ____, ____ · ____. La búsqueda literal de `casa` devolvió `[]`.

## 6. Evidencias

| # | Tipo | Descripción | Ruta |
| --- | --- | --- | --- |
| 1 | Captura | Corpus del proyecto: nueve pasajes con documento, código y sección (sección 2 del notebook). | Captura 1 |
| 2 | Captura | Consulta sobre trabajo remoto, con el ranking, el documento de origen y la similitud (sección 6). | Captura 2 |
| 3 | Captura | Batería de cinco pruebas y contraste con la búsqueda literal (sección 8). | Captura 3 |
| 4 | Notebook | Notebook ejecutado con el corpus del proyecto. | `Busqueda_Semantica_proyecto.ipynb` |

**Captura 1.** Corpus del proyecto.
*Pendiente: pegar aquí la captura 1 con tamaño, por ejemplo* `![[captura1.png|500]]`

**Captura 2.** Consulta sobre trabajo remoto.
*Pendiente: pegar aquí la captura 2, por ejemplo* `![[captura2.png|500]]`

**Captura 3.** Batería de pruebas y contraste literal.
*Pendiente: pegar aquí la captura 3, por ejemplo* `![[captura3.png|500]]`

## 7. Uso de inteligencia artificial

> [!important] Registrar la IA no reemplaza la explicación técnica. El equipo debe verificar, adaptar y comprender cualquier resultado utilizado.

| Herramienta | Objetivo o pregunta | Qué se utilizó | Cómo se verificó | Qué se modificó |
| --- | --- | --- | --- | --- |
| Claude | Revisar si el notebook coincidía con el proyecto y adaptar el corpus y las pruebas a DOC-1001 y DOC-1002. | Propuesta de corpus de nueve pasajes tomada de las políticas de la Clase 07, la función `mostrar()` con el documento de origen, la batería de pruebas y el borrador de las respuestas de cierre. | El equipo ejecutó el notebook en Colab, comparó los pasajes con las políticas originales y contrastó las respuestas esperadas con los puntajes reales. | Se reemplazaron el corpus, la consulta principal, el término literal, la batería de pruebas y las preguntas de cierre. Las respuestas de cierre se ajustaron con los puntajes obtenidos. |

## 8. Defensa técnica y retroalimentación

| Campo | Registro |
|---|---|
| Integrante que defendió | |
| Pregunta recibida | |
| Respuesta resumida | |
| Retroalimentación docente | El notebook usaba el corpus de demostración y no coincidía con el proyecto. |
| Mejora acordada | Reemplazar el corpus por las políticas del proyecto (DOC-1001 y DOC-1002) y mostrar el documento de origen en cada resultado. |

## 9. Aprendizajes

- **Concepto comprendido:** un embedding representa un texto como un vector que permite comparar significados. La búsqueda semántica recupera candidatos por cercanía, no respuestas: encuentra «trabajo remoto» aunque el usuario escriba «trabajar desde casa». Siempre hay un «más cercano», aunque ningún pasaje responda, así que hay que leer el texto recuperado y comprobar que contiene la información. Un pasaje que menciona un código (DOC-1002) no contiene necesariamente su estado.
- **Algo que aún genera duda:** [Escribir una duda real del equipo. Ej.: cómo decidir cuándo un puntaje bajo indica que no hay respuesta sin fijar un umbral con pocos ejemplos.]
- **Qué haríamos diferente:** [Escribir una mejora real del equipo. Ej.: usar desde el inicio el corpus del proyecto en vez del de demostración.]

## 10. Revisión antes de entregar

- [ ] Todos los integrantes registraron un aporte verificable.
- [ ] Los enlaces y rutas de evidencia funcionan.
- [ ] Los criterios de aceptación están actualizados.
- [ ] El uso de IA fue declarado y verificado.
- [ ] El equipo puede explicar las decisiones registradas.
