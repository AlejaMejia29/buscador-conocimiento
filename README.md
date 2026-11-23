# Buscador de conocimiento

Proyecto del curso **Inteligencia Artificial Generativa y Sistemas Inteligentes**, Institución Universitaria EAM, periodo 2026-II. Profesor: Robert Garcia Rey.

**Equipo:** Joan Sebastián Sosa Bedoya y Alejandra Mejía Patiño.

## Entrega final: aplicación web

La versión final del proyecto es una **aplicación web con Gradio** en [`app/`](app/): cada persona entra con su cuenta de Supabase Auth, pregunta sobre las políticas, recibe la respuesta con sus fuentes y recupera sus conversaciones, guardadas en Supabase. Instalación, configuración, despliegue y pruebas: [`app/README.md`](app/README.md). Documentación integral de los tres cortes: [`BITACORA_PROYECTO.md`](BITACORA_PROYECTO.md).

Lo que sigue en este archivo describe el notebook consolidado del segundo corte, que sigue siendo la forma de cargar el corpus en Supabase y de repetir la evaluación.

## Problema

En una organización, las respuestas sobre vacaciones, permisos o incapacidades están repartidas en políticas internas que pocas personas leen completas. Quien pregunta usa sus propias palabras («¿puedo trabajar desde casa toda la semana?») y no las del documento («trabajo remoto»), así que una búsqueda por palabras exactas no siempre encuentra la respuesta.

**Objetivo:** recuperar contenido por significado y entregar una respuesta pertinente **con referencia al documento de origen**, sin inventar plazos, requisitos ni estados.

**Usuarios:** empleados que consultan las políticas y el área de talento humano que las mantiene.

## Cómo funciona

```
Pregunta del usuario
   │
   ├─ Controles previos: entrada válida, solo lectura, vigencia sin código → se responde sin IA
   │
   ├─ Recuperación (configuración C)
   │     ├─ Semántica: embeddings MiniLM multilingüe + Supabase/pgvector (coseno)
   │     ├─ Léxica: BM25 sobre todo el corpus autorizado
   │     ├─ Fusión RRF por posiciones
   │     └─ Reranking con cross-encoder multilingüe → 3 pasajes
   │
   ├─ Generación: Groq (openai/gpt-oss-20b), JSON validado con Pydantic y citas [F1] comprobadas
   │
   ├─ Herramienta de vigencia (si la pregunta trae un código DOC-0000): solo lectura, argumentos validados
   │
   └─ Ficha final: respuesta, documento de origen, fragmento, estado y traza (latencia y tokens)
```

## Contenido del repositorio

| Ruta | Qué es |
|---|---|
| `app/` | Aplicación web final (Gradio, agente, RAG, MCP propio e historial en Supabase). |
| `BITACORA_PROYECTO.md` | Bitácora unificada de los tres cortes. |
| `notebooks/` | Notebooks de cada clase (02 a 11) con sus salidas. |
| `Buscador_Conocimiento_Final.ipynb` | Notebook final. Corre en Colab de principio a fin, sin otros notebooks ni archivos que subir. |
| `corpus/` | Documentos autorizados: `Politica_Recursos_Humanos.md` (DOC-1001) y `Politica_Permisos.md` (DOC-1002). Son ficticios. `Manual_Induccion` (DOC-1003) se excluye por estar desactualizado. |
| `supabase/esquema.sql` | Tabla `clase08_fragmentos`, seguridad por filas (RLS) y función `clase08_buscar_fragmentos`. |
| `supabase/historial.sql` | Conversaciones y mensajes por usuario, lectores autorizados del corpus y búsqueda de la aplicación. |
| `supabase/prueba_rls_local.sql` | Prueba de las políticas RLS en un PostgreSQL local. |
| `requirements.txt` | Versiones de las bibliotecas del notebook (las de la aplicación están en `app/requirements.txt`). |
| `bitacoras/` | Bitácoras de clase con sus capturas. |
| `evidencias/` | Métricas, respuestas, pruebas de continuidad y revisión humana de la ejecución final (sin claves). |
| `docs/` | Presentación del proyecto en PDF. |

## Cómo ejecutarlo

1. **Supabase:** crear un proyecto, ejecutar `supabase/esquema.sql` en el SQL Editor y crear un usuario en **Authentication → Users** (correo y contraseña, confirmado).
2. **Groq:** crear una clave en [console.groq.com](https://console.groq.com/keys).
3. **Colab:** abrir `Buscador_Conocimiento_Final.ipynb` en [Google Colab](https://colab.research.google.com/). En **Secretos** (icono de llave) crear estos cinco y darles acceso al notebook:

   | Secreto | Valor |
   |---|---|
   | `GROQ_API_KEY` | Clave de Groq |
   | `SUPABASE_URL` | Project URL (`https://<proyecto>.supabase.co`) |
   | `SUPABASE_PUBLISHABLE_KEY` | Clave publicable (`sb_publishable_...`). Nunca la clave secreta. |
   | `SUPABASE_EMAIL` | Correo del usuario de Supabase Auth |
   | `SUPABASE_PASSWORD` | Contraseña de ese usuario |

4. **Entorno de ejecución → Ejecutar todo.** No necesita GPU. La pregunta del usuario se escribe en el punto 10.

**Sin claves:** en el punto 2 se pueden desactivar `USAR_SUPABASE` (la búsqueda semántica se hace en memoria con los mismos vectores) y `GENERAR_CON_GROQ` (se evalúa solo la recuperación). El resto del notebook corre igual.

## Evaluación

Se compararon tres configuraciones con 15 preguntas anotadas antes de buscar (8 de desarrollo, 4 de reserva y 3 de comportamiento):

- **A · Semántica** (línea base).
- **B · Híbrida:** BM25 + semántica, fusionadas con RRF.
- **C · Híbrida + reranking** con cross-encoder. **Configuración elegida.**

Resultados de la Clase 09 en desarrollo (K = 3):

| Opción | Precision@3 | Recall@3 | Hit@3 | MRR |
|---|---|---|---|---|
| A · Semántica | 0,292 | 0,812 | 0,875 | 0,688 |
| B · Híbrida RRF | 0,333 | 0,875 | 0,875 | 0,729 |
| C · Híbrida + reranking | 0,333 | 0,938 | 1,000 | 0,875 |

En reserva, B y C empataron (Recall@3 = 1,0 frente a 0,75 de A). El notebook final repitió esta evaluación con los mismos valores.

Respuestas generadas en el notebook final (15 preguntas, mismo prompt y mismo modelo, revisión humana del equipo):

| Opción | Comportamiento esperado | Fallos |
|---|---|---|
| A · Semántica | 12 de 15 | D6 y R1 sin evidencia; C1 con error técnico |
| C · Híbrida + reranking | 15 de 15 | — |

Las métricas por caso, las respuestas completas, la revisión humana y las trazas están en `evidencias/`.

**Límites conocidos:** el corpus es pequeño (9 fragmentos); en preguntas compuestas el reranker puede dejar fuera una de las condiciones; una cita válida no garantiza que la afirmación sea fiel, por eso se revisan las respuestas a mano.

## Seguridad

- Las claves se leen de los Secretos de Colab; no están en el código ni en las salidas guardadas. La celda de exportación se detiene si encuentra una clave en la evidencia.
- Supabase se usa con clave publicable, usuario de Auth y RLS: cada usuario solo lee sus filas.
- La herramienta de vigencia es de solo lectura y solo acepta códigos que aparecen en la pregunta.
- Los documentos son ficticios y no contienen datos personales.
