---
tipo: bitacora-clase
curso: Inteligencia Artificial Generativa y Sistemas Inteligentes
periodo: EAM-2026II
equipo: SosaJoan-MejiaAlejandra
corte: 2
semana: "6"
clase: 8
fecha: 2026-10-13
estado: en-progreso
tags:
  - ai
  - bitacora
---

# Bitácora — Clase 8

## 1. Datos de la sesión

| Campo    | Registro |
| -------- | -------- |
| Tema     | Construcción de un sistema RAG: fragmentos en Supabase, recuperación y respuesta con Groq |
| Objetivo | Guardar el índice de la Clase 7 en Supabase, recuperar evidencia para una pregunta del proyecto y generar una respuesta citada, validada y comprobable al volver a conectarse. |
| Proyecto | Buscador de conocimiento |
| Inicio   | 6:00 |
| Cierre   | 9:30 |

## 2. Participación y responsabilidades

| Integrante                 | Asistió | Rol de la clase       | Responsabilidad asumida | Aporte verificable |
| -------------------------- | ------- | --------------------- | ----------------------- | ------------------ |
| Joan Sebastian Sosa Bedoya | Sí      | Integrante del equipo | Configurar Supabase, ejecutar el notebook y descargar la traza. | Sesión autenticada, 9 filas en `clase08_fragmentos` y `Evidencia RAG.json`. |
| Alejandra Mejia Patiño     | Sí      | Integrante del equipo | Contrastar cada respuesta con los fragmentos del corpus y registrar el fallo de la consulta ambigua. | Lectura de la respuesta útil de vacaciones y del caso «¿Cómo lo hago?». |

## 3. Reto aplicado al proyecto

### Funcionalidad trabajada

El Buscador de conocimiento pasa de devolver fragmentos a **responder con ellos**. Se reutilizó el índice de la Clase 7 (`Politica_Recursos_Humanos.md`, DOC-1001, y `Politica_Permisos.md`, DOC-1002; estrategia párrafos; 9 fragmentos). Esos registros se guardaron en Supabase y, ante una pregunta, el notebook calcula el embedding, llama a `clase08_buscar_fragmentos`, arma el contexto y pide a Groq una salida JSON con estado, respuesta, citas y limitación. Pydantic y una comprobación de etiquetas aceptan o rechazan esa salida. `DOC-1003` sigue excluido, como quedó en la configuración del índice.

### Lo que pedía la clase

Según la guía, el notebook y las diapositivas, el avance de esta sesión incluye:

- Proyecto de Supabase, usuario de Auth, script `Clase_08_Supabase_Setup.sql` y cinco secretos en Colab, sin claves administrativas ni contraseñas en las celdas.
- Cargar `Clase_07_Indice_y_Corpus.zip`, comprobar modelo, revisión y vectores de 384 componentes, y hacer `upsert` en `clase08_fragmentos`.
- Recorrido completo: pregunta, recuperación, lectura de candidatos, generación, validación y fuentes.
- Pruebas escritas antes de ejecutar: una pregunta respondible y su paráfrasis, una consulta ambigua, una fuera del corpus y un dato actual que el texto no contiene.
- Volver a consultar con otro cliente, sin cargar de nuevo las filas, y conservar la traza.
- En la bitácora: corpus, configuración, prompt, notebook, una respuesta útil y una limitación, con qué afirmación tenía respaldo.

El anexo de PDF, OCR, Excel y Word es opcional. El corpus del proyecto ya estaba en Markdown desde la Clase 7.

### Criterios de aceptación

- [x] Iniciar sesión con un usuario de Supabase Auth y la clave publicable. La salida fue «Sesión de práctica iniciada. Las credenciales permanecen privadas.»
- [x] Abrir el ZIP de la Clase 7 y comprobar 9 fragmentos, matriz `(9, 384)` y la revisión `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`.
- [x] Cargar las 9 filas con `upsert`. La lectura posterior devolvió `Filas: 9` y una fuente `Politica_Permisos.md`.
- [x] Recuperar con la función SQL filtrando propietario, `corpus_id`, modelo y revisión. `k = 3`.
- [x] Generar con `openai/gpt-oss-20b`, temperatura 0, `reasoning_effort` low y contrato Pydantic (`respondida`, `parcial`, `aclaracion`, `evidencia_insuficiente`).
- [x] Mostrar la fuente citada (archivo, sección, versión e identificador del fragmento).
- [x] Consultar de nuevo con otro cliente y obtener los mismos fragmentos y puntajes, sin un segundo `upsert`.
- [x] Guardar la traza (`Evidencia RAG.json`, 6 respuestas aceptadas).
- [x] Dejar una respuesta útil con cita respaldada y un fallo observado.
- [ ] Reescribir en el notebook las cinco pruebas del punto 9 para que el estado «esperado» corresponda a este corpus. Siguen las preguntas y los estados del ejemplo de constancias y acceso.
- [ ] Ejecutar, además de la consulta principal, una segunda redacción de la misma regla de vacaciones.

### Archivos o componentes modificados

- `RAG Supabase Groq.ipynb`: notebook de la clase ejecutado en Colab. En el punto 8 se añadió `REGLA_CITAS` al prompt y se ajustó `validar_respuesta` para normalizar etiquetas (`[F1]` y `F1`).
- `Evidencia RAG.json`: configuración, prompt `rag_v1`, seis trazas, candidatos, estados y uso de tokens informado por Groq.
- Supabase, tabla `public.clase08_fragmentos`, corpus `soporte_didactico-7d84714b942f`. El nombre base se dejó en el valor del notebook; la huella `7d84714b942f` identifica esta construcción del ZIP.

## 4. Decisiones técnicas

| Decisión | Razón | Alternativa descartada |
| --- | --- | --- |
| Reutilizar el índice de párrafos de la Clase 7, con el mismo modelo y la misma revisión | La pregunta y los fragmentos tienen que compartir representación. El punto 4 comprobó dos muestras: el producto punto con el vector guardado superó 0.999. | Volver a fragmentar o cambiar de modelo de embeddings en esta sesión. |
| Búsqueda exacta en `clase08_buscar_fragmentos` (distancia coseno de pgvector, `security invoker`) | Hay 9 fragmentos. La función limita por `owner_id`, corpus, modelo y revisión, y devuelve como máximo 3 candidatos. | Crear un índice aproximado HNSW o IVFFlat. |
| RLS: cada usuario autenticado solo lee e inserta sus filas. Clave `sb_publishable_`, sin `service_role` | El notebook se comparte; las credenciales no. El acceso no depende de conocer `CORPUS_BASE`. | Desactivar RLS o usar la clave administrativa en Colab. |
| `CORPUS_ID = soporte_didactico-7d84714b942f` | La huella separa esta construcción de un índice futuro. Repetir el `upsert` actualiza las mismas filas (clave `owner_id, corpus_id, chunk_id`). | Borrar versiones anteriores para «limpiar» la tabla. |
| Añadir `REGLA_CITAS` y normalizar las etiquetas antes de aceptar la salida | Groq a veces devolvía las citas con corchetes o en un formato que el validador original rechazaba. La regla pide `["F1"]` en el campo y `[F1]` en el texto. El validador une las etiquetas del JSON y las del texto, y rechaza las que no están en el contexto. | Aceptar el texto de Groq sin validar, o descartar la respuesta por un detalle de formato. |
| Estado `parcial` en la pregunta de vacaciones | El fragmento dice que, con menos anticipación, la solicitud no se aprueba sola y queda sujeta a la disponibilidad del área. Esa disponibilidad concreta no está en el corpus. | Forzar `respondida` y omitir el límite. |
| Dejar el anexo de extracción sin documento nuevo | Las fuentes del proyecto ya son Markdown con código, versión y huella. La celda de PDF se interrumpió en la subida (`KeyboardInterrupt`) y no quedó un corpus extraído. | Indexar un PDF sin revisar el texto derivado. |

## 5. Problemas y soluciones

| Problema encontrado | Causa identificada | Solución aplicada | ¿Cómo se verificó? |
| --- | --- | --- | --- |
| **Fallo:** «¿Cómo lo hago?» quedó en `respondida` y explicó el trámite de vacaciones en tres pasos, con citas [F1] y [F2]. Lo esperado para una pregunta sin decir de qué trámite se trata es `aclaracion`. | Los tres candidatos son de vacaciones y permisos, con similitudes 0.090, 0.053 y 0.046. Siempre hay un «más cercano». El modelo tomó esos pasajes como si la pregunta fuera el procedimiento de vacaciones. Las citas existen, así que la validación formal pasó; el texto no responde a una pregunta que no dice el trámite. | Se registra el fallo. El contrato comprueba que la etiqueta exista, no que la afirmación sea la que la pregunta pedía. En la Clase 9 conviene un estado `aclaracion` cuando la similitud es tan baja y la pregunta no nombra el tema. | Traza 3 de `Evidencia RAG.json` y salida del punto 9. |
| Las pruebas de constancia y de error 403 quedaron en `evidencia_insuficiente`, mientras el notebook marcaba `respondida`. | Esas preguntas y sus estados esperados pertenecen al corpus de ejemplo (acceso y constancias). El ZIP cargado es el de políticas de vacaciones y permisos. El modelo se negó a inventar la entrega de una constancia o la suspensión de una cuenta. | Se conserva el resultado como límite correcto de este corpus. Falta cambiar el «esperado» del punto 9 para que la batería evalúe las políticas del proyecto. | Punto 9: observado `evidencia_insuficiente` en ambas. Ningún fragmento recuperado habla de constancias ni de un error 403. |
| «¿Cuáles son los requisitos para solicitar una beca?» recuperó primero permisos laborales (0.563), por la palabra «requisitos». | La similitud acerca temas de «solicitud» aunque el documento no hable de becas. | El modelo eligió `evidencia_insuficiente`, sin citar, y explicó que la evidencia es de permisos y vacaciones. | Traza 4. Estado esperado y observado coinciden. |
| «¿Cuál es el estado actual de SOL-1001?» acercó los párrafos de vigencia de DOC-1001 (0.284) y DOC-1002 (0.259). | Comparten la frase «estado actual del documento». Ninguno es la solicitud SOL-1001 ni trae un estado individual. | `evidencia_insuficiente`, sin inventar el estado. La vigencia de un documento, cuando haga falta, sigue en la herramienta del repositorio (Clase 4), no en estos párrafos. | Traza 5. La respuesta dice que la evidencia no menciona SOL-1001. |

### Consulta principal (punto 6 y punto 8)

Pregunta: «¿Me aprueban las vacaciones si las pido con poca anticipación?»

| Etiqueta | Fragmento | Coseno |
| --- | --- | --- |
| F1 | DOC-1001 · Vacaciones · párrafo 5. Menos anticipación: no se aprueba automáticamente y queda sujeta a la disponibilidad del área. También exige un año de servicio. | 0.592 |
| F2 | DOC-1001 · Vacaciones · párrafo 6. El jefe responde en cinco días hábiles; no se acumulan más de dos periodos. | 0.562 |
| F3 | DOC-1001 · Vacaciones · párrafo 4. La solicitud se registra con al menos quince días hábiles. | 0.451 |

Resultado aceptado:

- **Estado:** `parcial`
- **Respuesta:** si la solicitud llega con poca anticipación, no se aprueba automáticamente y queda sujeta a la disponibilidad del área; no hay garantía de aprobación. Cita [F1].
- **Limitación registrada:** no hay datos de la disponibilidad concreta del área ni criterios adicionales.
- **Respaldo:** la frase citada está en F1. La afirmación «no hay garantía» corresponde a «no se aprueba automáticamente». F1 también condiciona las vacaciones a un año de servicio; la respuesta no usó esa condición porque la pregunta era la anticipación.
- **Qué no quedó citado:** el plazo de quince días hábiles está en F3. La respuesta habla de «la anticipación requerida» sin repetir esa cifra, así que no cita F3. Por eso `parcial` es el estado adecuado.
- **Generación:** 397 ms. Prompt 747 tokens, completado 167 (63 de razonamiento), total 914. Temperatura 0.

### Batería del punto 9

El punto 9 se ejecutó (`EJECUTAR_PRUEBAS = True`). Cada fila es una llamada a Groq.

| # | Pregunta | Caso que cubre | Esperado en el notebook | Observado | Lectura para este corpus |
| --- | --- | --- | --- | --- | --- |
| 1 | ¿Me aprueban las vacaciones si las pido con poca anticipación? | Pregunta respondible, paráfrasis de la regla de anticipación | (consulta del punto 6, no está en la lista del punto 9) | `parcial`, cita [F1] | Útil. La condición y la consecuencia se conservan. |
| 2 | Si todavía no adjunto todos los documentos, ¿me entregan la constancia? | Pregunta del ejemplo didáctico | `respondida` | `evidencia_insuficiente` | Correcto aquí: el corpus no tiene esa política. El «esperado» del notebook no se actualizó. |
| 3 | ¿Cómo lo hago? | Ambigua | `aclaracion` | `respondida` | **Fallo.** Inventó el trámite de vacaciones. |
| 4 | ¿Cuáles son los requisitos para solicitar una beca? | Fuera del corpus | `evidencia_insuficiente` | `evidencia_insuficiente` | Acierto. Había candidatos y aun así no respondió con ellos. |
| 5 | ¿Cuál es el estado actual de SOL-1001? | Dato actual, ausente del texto | `parcial` o `evidencia_insuficiente`, sin inventar el estado | `evidencia_insuficiente` | Acierto. No inventó el estado. |
| 6 | Me aparece un error 403, ¿mi cuenta está suspendida? | Pregunta del ejemplo didáctico | `respondida`, sin afirmar suspensión | `evidencia_insuficiente` | Correcto aquí: no hay política de cuentas. Tampoco afirmó que la cuenta estuviera suspendida. |

### Persistencia

El punto 10 abrió otro cliente, inició sesión con el mismo usuario y repitió la consulta de vacaciones. La aserción comparó `chunk_id`, texto y similitud (`np.allclose`). La salida fue: «Otro cliente recuperó los mismos fragmentos, sin volver a cargar el corpus.» Respuestas aceptadas en la traza: 6.

## 6. Evidencias

| Tipo | Descripción | Enlace o ruta |
| --- | --- | --- |
| Notebook | Ejecución en Colab de los puntos 1 a 10. Celdas 94 a 105. | `Clase 8/RAG Supabase Groq.ipynb` |
| Traza | Configuración de embeddings, prompt, seis consultas, candidatos, estados y tokens. | `Clase 8/Evidencia RAG.json` |
| Índice de origen | ZIP de la Clase 7 subido en el punto 3 (`Clase_07_Indice_y_Corpus.zip`). Fragmentos: 9. Matriz: `(9, 384)`. | Salida del punto 3 en el notebook |
| Corpus | `Politica_Recursos_Humanos.md` (DOC-1001) y `Politica_Permisos.md` (DOC-1002). Excluido: `Manual_Induccion` (DOC-1003). | `configuracion_embeddings` dentro de `Evidencia RAG.json` |
| Supabase | Tabla `clase08_fragmentos`, función `clase08_buscar_fragmentos`, corpus `soporte_didactico-7d84714b942f`, 9 filas del usuario de la sesión. | Salida del punto 5 y recuperación del punto 6 |

Configuración registrada en la traza:

| Campo | Valor |
| --- | --- |
| Modelo de embeddings | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| Revisión | `e8f8c211226b894fcb81acc59f3b34ba3efd5f42` |
| Estrategia | `parrafos` |
| Máximo de tokens / solapamiento | 80 / 12 |
| Similitud | coseno, vectores normalizados, `max_seq_length` 128 |
| Modelo generativo | `openai/gpt-oss-20b` |
| Prompt | `rag_v1`, más la regla de formato de citas añadida en el punto 8 |
| k | 3 |

## 7. Uso de inteligencia artificial

> [!important] Registrar la IA no reemplaza la explicación técnica. El equipo debe verificar, adaptar y comprender cualquier resultado utilizado.

| Herramienta | Objetivo o pregunta | Qué se utilizó | Cómo se verificó | Qué se modificó |
| --- | --- | --- | --- | --- |
| Groq (`openai/gpt-oss-20b`) | Redactar la respuesta a partir de los fragmentos recuperados. | Seis salidas JSON de la sesión (consulta principal y punto 9). | Pydantic, comprobación de que cada cita exista en el contexto, y lectura humana del pasaje F1 y del fallo «¿Cómo lo hago?». | Se añadió `REGLA_CITAS` y la normalización de etiquetas en `validar_respuesta`. El contenido de las políticas no se reescribió. |
| Cursor | Redactar esta bitácora a partir del notebook ejecutado, de `Evidencia RAG.json` y de la guía de la Clase 8. | Borrador de las secciones 3, 4, 5 y 9, con los puntajes y estados de la traza. | El equipo contrasta esta bitácora con la salida de Colab y con `Evidencia RAG.json`. | Se reemplazó el texto de la Clase 7, que seguía en este archivo, por el registro de la sesión del 13 de octubre. |

## 8. Defensa técnica y retroalimentación

| Campo | Registro |
| --- | --- |
| Integrante que defendió | |
| Pregunta recibida | |
| Respuesta resumida | |
| Retroalimentación docente | |
| Mejora acordada | |

## 9. Aprendizajes

- **Concepto comprendido:** RAG separa tres trabajos. El embedding y Supabase eligen candidatos; Groq redacta solo con esos pasajes; el programa comprueba el formato y que la cita exista. Que una etiqueta sea válida no demuestra que la afirmación responda la pregunta. En «¿Cómo lo hago?» las citas [F1] y [F2] apuntan a fragmentos reales y, aun así, la respuesta trata un trámite que la persona no nombró.
- **Algo que aún genera duda:** Cómo decidir, antes de llamar a Groq, que una similitud tan baja (0.09) y una pregunta sin tema deben pedir aclaración, en lugar de dejar que el modelo complete el trámite más cercano.
- **Qué haríamos diferente:** Cambiar las cinco preguntas del punto 9 para que hablen de vacaciones y permisos, y anotar el estado esperado con este corpus antes de ejecutar. Añadir una segunda redacción de la misma regla de quince días. Subir la versión del prompt cuando se añade `REGLA_CITAS`, para que la traza distinga el prompt del notebook original.

## 10. Revisión antes de entregar

- [x] Todos los integrantes registraron un aporte verificable.
- [x] Los enlaces y rutas de evidencia funcionan.
- [x] Los criterios de aceptación están actualizados.
- [x] El uso de IA fue declarado y verificado.
- [ ] El equipo puede explicar las decisiones registradas.
