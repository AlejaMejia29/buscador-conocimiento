# Buscador de conocimiento · Aplicación web

Aplicación final del proyecto del curso **Inteligencia Artificial Generativa y Sistemas Inteligentes** (EAM 2026-II, profesor Robert Garcia Rey). Equipo: Joan Sebastián Sosa Bedoya y Alejandra Mejía Patiño.

- Bitácora unificada de los tres cortes: [`../BITACORA_PROYECTO.md`](../BITACORA_PROYECTO.md)
- Presentación: [`presentacion_proyecto.pdf`](presentacion_proyecto.pdf)
- Notebook consolidado y evaluación del segundo corte: [`../Buscador_Conocimiento_Final.ipynb`](../Buscador_Conocimiento_Final.ipynb), [`../evidencias/`](../evidencias/)

## Problema, usuarios y alcance

Las reglas sobre vacaciones, permisos, trabajo remoto e incapacidades están repartidas en políticas internas que pocas personas leen completas. Quien pregunta usa sus propias palabras («¿puedo trabajar desde casa?») y no las del documento («trabajo remoto»).

La aplicación responde preguntas sobre esas políticas con la **referencia al documento de origen** de cada afirmación, y consulta la **vigencia** de un documento por su código (`DOC-0000`) mediante una herramienta MCP. La usan los empleados de una organización ficticia; cada persona entra con su propia cuenta y conserva sus conversaciones.

**Fuera del alcance:** aprobar vacaciones o permisos, cambiar el estado de un documento, responder sobre temas que no están en las políticas o mostrar datos de otros usuarios. La aplicación solo lee. Las respuestas son orientativas y se contrastan con el documento citado.

**Datos de la demostración:** dos políticas ficticias del repositorio, [`../corpus/`](../corpus/): `Politica_Recursos_Humanos.md` (DOC-1001) y `Politica_Permisos.md` (DOC-1002). `Manual_Induccion` (DOC-1003) se excluye por desactualizado.

## Arquitectura y procedencia del código

```
Navegador ── app.py (Gradio) ─────────────────────────────────────────────
   │  ingreso con correo y contraseña → almacenamiento.py → Supabase Auth
   │  pregunta → sistema.py.atender(texto, cliente_del_usuario, historial)
   │                │
   │                ├─ Agente (Groq openai/gpt-oss-20b, decisión JSON validada con Pydantic)
   │                │     ├─ buscar_documentos → RAG opción C
   │                │     │     semántica (Supabase pgvector, sesión del usuario, RLS)
   │                │     │     + BM25 → fusión RRF → reranking con cross-encoder → 3 pasajes [F1..F3]
   │                │     ├─ consultar_estado_documento → MCP propio por stdio → [T1]
   │                │     ├─ aclarar / rechazar
   │                │     └─ responder (citas comprobadas)
   │                └─ traza: estado, respuesta, citas, fuentes, recorrido, duración
   └─ almacenamiento.py guarda pregunta y respuesta en Supabase y la interfaz muestra lo guardado
```

| Archivo | Responsabilidad | Procedencia |
|---|---|---|
| `app.py` | Interfaz de Gradio: ingreso, lista de conversaciones, chat, fuentes y estado. Guarda en `gr.State` solo la sesión y la conversación activa. | Nuevo (Clase 12). Reemplaza la celda de entrada del punto 7 de la Clase 11. |
| `sistema.py` | Configuración, RAG (opción C), contratos Pydantic, controles, agente y cliente MCP. No guarda estado de ningún usuario. | Puntos 2, 3, 4, 5 y 6 del notebook de la Clase 11, con la recuperación elegida en la Clase 09. |
| `almacenamiento.py` | Inicio de sesión con Supabase Auth, cliente por solicitud, creación y listado de conversaciones, carga y guardado de mensajes. Comprueba el propietario antes de leer o escribir. | Nuevo. Reemplaza el diccionario `MEMORIA` de la Clase 11. |
| `servidor_mcp.py` | Servidor MCP propio con la herramienta de solo lectura `consultar_estado_documento`. | Punto 4 de la Clase 11 (antes era un texto que el notebook escribía en disco); registros de la Clase 04. |
| `pruebas/test_controles.py` | Pruebas sin claves: MCP real, contratos, límites, citas, recorrido del agente con un modelo simulado e historial. | Punto 8 de la Clase 11. |
| `Probar_en_Colab.ipynb` | Abre la aplicación desde Colab con un enlace temporal, para probarla sin instalar nada. No es la aplicación. | Nuevo. |
| `../supabase/historial.sql` | Tablas de conversaciones y mensajes, RLS, lectores autorizados del corpus y función de búsqueda de la aplicación. | Nuevo. |

**Qué se guarda y qué se envía al modelo.** Se guardan todos los mensajes de cada conversación, con su estado y sus fuentes. Al modelo solo se envían los **últimos 4 turnos completos** de la conversación activa, como la ventana de memoria de la Clase 11. La memoria sirve para entender «ese documento»; no es evidencia: toda afirmación sobre las políticas exige una búsqueda en el turno actual.

**Cambios respecto de la Clase 11.**
- La memoria pasa de un diccionario de Colab a Supabase, por usuario y por conversación.
- Se quitó la acción `guardar_informe` y el Filesystem MCP: escribir archivos en el disco del servidor no sirve en una aplicación publicada y no aportaba al usuario. La aplicación queda de solo lectura.
- Se aplicó el ajuste pendiente de la prueba P11: si el modelo intenta responder sobre un tema de las políticas sin una cita F, el programa lo bloquea y le pide buscar primero; si insiste, el turno termina como `SIN_EVIDENCIA_DOCUMENTAL`.

## Requisitos

- Python **3.11 o superior** (probado con 3.12 en Colab y 3.13 en Linux). Usa `asyncio.timeout`.
- Dependencias con versión fija en [`requirements.txt`](requirements.txt). `sentence-transformers` instala PyTorch.
- Cuenta de **Groq** con clave de API.
- Proyecto de **Supabase** con: el corpus del RAG en `clase08_fragmentos` (Clase 08), usuarios en Auth y las tablas de [`../supabase/historial.sql`](../supabase/historial.sql).
- Unos 2 GB de RAM: el modelo de embeddings y el reranker se cargan una vez al arrancar (aprox. 470 MB cada uno en disco). La primera ejecución los descarga de Hugging Face.
- No requiere Node: el MCP es propio y corre con el mismo Python.

## Instalación desde un clon limpio

PowerShell:

```powershell
git clone https://github.com/AlejaMejia29/buscador-conocimiento
cd buscador-conocimiento
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r app/requirements.txt
Copy-Item app/.env.ejemplo app/.env
```

Linux/macOS:

```bash
git clone https://github.com/AlejaMejia29/buscador-conocimiento
cd buscador-conocimiento
python3 -m venv .venv
.venv/bin/python -m pip install -r app/requirements.txt
cp app/.env.ejemplo app/.env
```

Sin instalar nada: abrir [`Probar_en_Colab.ipynb`](Probar_en_Colab.ipynb) en Colab y seguir sus cuatro celdas.

## Variables y secretos

La aplicación lee `app/.env` (con `python-dotenv`) o las mismas variables desde el panel del alojamiento. `app/.env` está en `.gitignore`; solo se publica [`.env.ejemplo`](.env.ejemplo).

| Variable | Uso | ¿Obligatoria? |
|---|---|---|
| `GROQ_API_KEY` | Clave de Groq para el agente. | Sí |
| `GROQ_MODEL` | Modelo probado: `openai/gpt-oss-20b`. | No (ese es el valor por defecto) |
| `SUPABASE_URL` | Project URL de Supabase (`https://<proyecto>.supabase.co`). | Sí |
| `SUPABASE_PUBLISHABLE_KEY` | Clave publicable (`sb_publishable_...`). No identifica a un usuario; la aplicación rechaza claves administrativas. | Sí |
| `CORPUS_ID` | Corpus cargado con el notebook final: `buscador_conocimiento-29dccc23ac01`. | Sí |
| `CORPUS_PROPIETARIO_ID` | UUID de la cuenta de Supabase que cargó el corpus. No es un secreto. | Sí |
| `EMBEDDINGS_REVISION` | Revisión exacta del modelo de embeddings con la que se calcularon los vectores. | Sí |
| `GRADIO_SERVER_NAME` | `127.0.0.1` en local, `0.0.0.0` en un alojamiento. | No (por defecto `127.0.0.1`) |
| `PORT` | Puerto HTTP. El alojamiento lo suministra. | No (por defecto `7860`) |
| `GRADIO_SHARE` | `1` crea un enlace temporal `*.gradio.live` (solo para pruebas en Colab). | No |
| `MODO_PRUEBAS` | `1` muestra la casilla para simular la caída del servidor MCP. | No |

No hay correos ni contraseñas en `.env`: cada persona escribe los suyos en la pantalla de ingreso y obtiene su propia sesión de Supabase Auth.

## Preparar el corpus y los datos

El corpus se carga **una sola vez** con el notebook consolidado [`../Buscador_Conocimiento_Final.ipynb`](../Buscador_Conocimiento_Final.ipynb) (puntos 3 a 5), iniciando sesión con la cuenta que será propietaria del corpus. Ese notebook limpia los dos documentos, los divide en 9 fragmentos por párrafos (máximo 80 tokens, solapamiento 12), calcula embeddings con `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensiones, normalizados, revisión `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`) y los guarda en `clase08_fragmentos`. El identificador `buscador_conocimiento-29dccc23ac01` es una huella del texto, los metadatos y la configuración: si alguien carga el mismo corpus obtiene el mismo identificador.

Al atender una pregunta la aplicación **no vuelve a insertar el corpus**: solo lo lee. La primera búsqueda carga los 9 fragmentos (para BM25) con la sesión de quien pregunta y los conserva en memoria; cada búsqueda semántica vuelve a pasar por Supabase con la sesión del usuario y comprueba que los fragmentos no hayan cambiado.

Para conocer el `CORPUS_PROPIETARIO_ID`, en Supabase → SQL Editor:

```sql
select distinct owner_id, corpus_id, count(*) from public.clase08_fragmentos group by 1, 2;
```

**Quién puede leer el corpus.** El corpus pertenece a la cuenta que lo cargó (`owner_id = auth.uid()`, Clase 08). Las demás cuentas solo lo leen si su propietario las autoriza en la tabla `buscador_corpus_lectores` (paso 4 de `historial.sql`). Esa autorización no da acceso a ningún historial: las conversaciones siguen siendo privadas de cada persona. Una cuenta no autorizada puede ingresar y conversar, pero sus búsquedas terminan en el estado `SIN_ACCESO_CORPUS`.

## Usuarios e historiales

1. En Supabase → SQL Editor, ejecutar [`../supabase/esquema.sql`](../supabase/esquema.sql) solo si el proyecto todavía no tiene la tabla de la Clase 08, y después [`../supabase/historial.sql`](../supabase/historial.sql).
2. En **Authentication → Users → Add user**, crear las cuentas de prueba con correo y contraseña (marcar *Auto Confirm User*).
3. Autorizar a cada cuenta que no sea la propietaria del corpus con el `insert` comentado al final de `historial.sql`.

**Tablas.**

| Tabla | Columnas | Reglas RLS |
|---|---|---|
| `buscador_conversaciones` | `id` (uuid), `usuario_id` (uuid, por defecto `auth.uid()`), `titulo`, `creada_en` | Leer, crear y renombrar solo si `usuario_id = auth.uid()`. |
| `buscador_mensajes` | `id` (identidad, da el orden estable), `conversacion_id`, `usuario_id`, `rol` (`usuario`/`asistente`), `contenido`, `estado`, `fuentes` (jsonb), `creado_en` | Leer e insertar solo si el mensaje es del usuario **y** la conversación es suya. No hay políticas de edición ni borrado. |
| `buscador_corpus_lectores` | `owner_id`, `corpus_id`, `usuario_id` | Cada usuario ve solo sus autorizaciones; nadie puede insertarlas desde la aplicación. |

`historial.sql` también retira los privilegios que Supabase concede por defecto a `anon` y `authenticated` y deja solo los que usa la aplicación.

**Identidad y sesión.** `almacenamiento.py` crea un **cliente de Supabase nuevo en cada solicitud** con la sesión de esa persona. `set_session` valida el token con Supabase Auth (o lo renueva si expiró), así que el `usuario_id` sale del servidor de autenticación y no del navegador. `gr.State` guarda solo esa sesión y el id de la conversación activa. No existe un cliente global autenticado compartido.

**Recuperación del historial.** Al ingresar se listan las conversaciones de la cuenta desde Supabase; al elegir una, se cargan sus mensajes en orden. Después de cada pregunta, la interfaz vuelve a leer los mensajes de Supabase y muestra lo que quedó guardado. Como nada vive en el servidor de la aplicación, el historial sobrevive al refrescar la página, cerrar sesión y reiniciar la aplicación. «Nueva conversación» no borra las anteriores.

## Configuración del MCP

| Campo | Valor |
|---|---|
| Servidor | `servidor_mcp.py`, propio: «Vigencia de documentos · Buscador de conocimiento» |
| SDK | `mcp==2.3.0` (`MCPServer` y `Client`) |
| Transporte | stdio. La aplicación lo arranca como proceso hijo con el mismo Python en cada consulta; no abre puertos. |
| Herramientas | Una: `consultar_estado_documento(codigo_documento)`, solo lectura, código validado con `^DOC-[0-9]{4}$` en el servidor y en la aplicación. |
| Datos | Registros ficticios de la Clase 04 (DOC-1001 vigente, DOC-1002 en revisión, DOC-1003 desactualizado). |

Al arrancar, la aplicación descubre el catálogo y se niega a continuar si el servidor ofrece herramientas distintas de la esperada. El agente solo puede consultar un código que el usuario escribió en esa conversación. Un código inexistente devuelve `encontrada: false` (no es un error técnico); un argumento inválido lo rechaza el servidor; un servidor caído se informa como `ERROR_TECNICO`. Cada operación tiene un límite de repetición por turno. No hay acciones sensibles, así que no se requiere aprobación humana. Los errores del proceso MCP se escriben en `app/mcp.log` (no se publica).

## Ejecución local

Desde la raíz del clon, con `app/.env` completo:

```powershell
cd app
..\.venv\Scripts\python.exe app.py
```

Linux/macOS: `cd app && ../.venv/bin/python app.py`.

La consola muestra `Preparando modelos y servidor MCP (solo una vez)...` y luego la URL local, por defecto <http://127.0.0.1:7860>. Se detiene con `Ctrl + C`. El servidor MCP no se inicia aparte: lo arranca la aplicación.

**Pruebas sin claves** (desde `app/`): `python -m pytest pruebas -q`.

## Despliegue

**Estado (2026-11-24):** la aplicación no tiene una URL permanente. Se ejecutó y se probó desde una URL pública temporal de Gradio (`*.gradio.live`) lanzada desde Colab con [`Probar_en_Colab.ipynb`](Probar_en_Colab.ipynb). Todas las pruebas de la sección siguiente se hicieron desde esa URL, con Supabase y Groq reales. El enlace dura hasta una semana y solo mientras la celda de Colab esté en ejecución.

**Por qué no hay URL permanente (bloqueo registrado):**

| Alojamiento | Resultado |
|---|---|
| Render, plan gratuito | 512 MB de RAM. La aplicación necesita unos 2 GB para PyTorch, el modelo de embeddings y el reranker, así que no arranca. El plan con 2 GB es de pago. |
| Hugging Face Spaces | Desde noviembre de 2026 publicar un Space de Gradio exige el plan PRO. Respuesta del servidor al crear el Space: `402 Payment Required … hosting Gradio and Docker Spaces on free cpu-basic requires a PRO subscription`. |
| Netlify | Solo sirve sitios estáticos; no ejecuta un servidor Python. |
| Google Cloud Run | Funciona dentro del nivel gratuito, pero exige registrar una tarjeta en la cuenta de facturación. Dejamos la imagen lista (abajo). |

**Cómo publicarla con una URL permanente cuando haya un alojamiento disponible.**

*Google Cloud Run* (desde Cloud Shell en el navegador, con [`Dockerfile`](Dockerfile)):

```bash
git clone https://github.com/AlejaMejia29/buscador-conocimiento
cd buscador-conocimiento/app
gcloud run deploy buscador-conocimiento --source . --region us-central1 \
  --memory 4Gi --cpu 2 --max-instances 1 --allow-unauthenticated \
  --set-env-vars SUPABASE_URL=...,CORPUS_ID=buscador_conocimiento-29dccc23ac01,CORPUS_PROPIETARIO_ID=...,EMBEDDINGS_REVISION=e8f8c211226b894fcb81acc59f3b34ba3efd5f42,GROQ_API_KEY=...,SUPABASE_PUBLISHABLE_KEY=...
```

`--max-instances 1` mantiene cada sesión de Gradio en el mismo contenedor. Las claves conviene pasarlas con Secret Manager (`--set-secrets`) en lugar de `--set-env-vars`.

*Hugging Face Spaces con plan PRO:* [`Desplegar_en_HF.ipynb`](Desplegar_en_HF.ipynb) crea el Space, configura variables y secretos desde los Secretos de Colab (más `HF_TOKEN` con permiso Write) y sube los archivos de `app/` con el `README.md` de [`despliegue_hf/`](despliegue_hf/README.md).

*Render con una instancia de al menos 2 GB:* Web Service con **Root Directory `app`**, **Build Command `pip install -r requirements.txt`**, **Start Command `python app.py`**, las mismas variables en *Environment* y `GRADIO_SERVER_NAME=0.0.0.0` (la aplicación lee `PORT`).

En todos los casos el corpus y los historiales viven en Supabase; el disco del alojamiento no guarda nada que haya que conservar. Por eso el historial se recuperó igual después de reiniciar Colab (prueba H3).

## Pruebas y resultados observados

Pruebas automáticas sin claves (`python -m pytest pruebas -q`), ejecutadas el 2026-11-24 en Linux con Python 3.13 y en Colab: **16 aprobadas**. Cubren el servidor MCP real (catálogo, consulta vigente, código inexistente, argumento inválido y caída simulada), código no aportado, citas normalizadas e inexistentes, respuesta sobre políticas sin fuente, límites de operaciones y repetición, RRF, rechazo de clave administrativa, recorrido del agente con modelo simulado, ventana del historial, rechazo de solicitudes fuera del corpus y consulta de vigencia con el código del fragmento.

Políticas RLS, probadas el 2026-11-23 con [`../supabase/prueba_rls_local.sql`](../supabase/prueba_rls_local.sql) en PostgreSQL 16 con pgvector y un esquema `auth` que imita el de Supabase:

| Caso | Esperado | Observado |
|---|---|---|
| Cuenta autorizada busca en el corpus | 3 filas | 3 filas |
| Cuenta no autorizada busca en el corpus | 0 filas | 0 filas |
| Cuenta autorizada intenta insertar en el corpus ajeno | Rechazo | Rechazado por RLS |
| Una cuenta se autoriza a sí misma o a otra como lectora | Rechazo | Permiso denegado |
| Crear una conversación a nombre de otra cuenta | Rechazo | Rechazado por RLS |
| Leer conversación y mensajes ajenos conociendo el UUID | 0 filas | 0 y 0 filas |
| Insertar un mensaje en una conversación ajena | Rechazo | Rechazado por RLS |
| Renombrar una conversación ajena | 0 filas cambiadas | 0 filas, título intacto |
| Borrar mensajes | Rechazo | Permiso denegado |
| Rol `anon` lee historial o busca | Rechazo | Permiso denegado |

Pruebas desde la aplicación con Supabase y Groq reales, el 2026-11-24 desde Colab (enlace temporal de Gradio), con `usuario1@prueba.com` y `usuario2@prueba.com`, ambas autorizadas como lectoras del corpus `buscador_conocimiento-29dccc23ac01`. Capturas en [`../evidencias/capturas_app/`](../evidencias/capturas_app/).

| # | Entrada o acción | Ruta o resultado esperado | Observado | Evidencia |
|---|---|---|---|---|
| A1 | «¿Con cuánta anticipación debo pedir las vacaciones?» | `responder` con [F] de DOC-1001 | «al menos quince días hábiles de anticipación [F1]», fuente Politica_Recursos_Humanos.md | [A1](../evidencias/capturas_app/A1_vacaciones_con_fuente.png) |
| A2 | «¿Cuántos días de vacaciones tengo al año?» (el corpus no lo dice) | Reconoce el límite, sin inventar | «La política de Recursos Humanos no indica la cantidad de días…», sin cifra inventada | [A2](../evidencias/capturas_app/A2_sin_evidencia.png) |
| A3 | «¿Cómo lo hago?» en una conversación nueva | `aclarar` | Pregunta si se refiere a vacaciones, permisos, trabajo remoto o incapacidades | [A3](../evidencias/capturas_app/A3_A6_H1_aclarar_falla_mcp.png) |
| A4 | «¿Cuántos días de trabajo remoto puedo tener por semana? ¿Ese documento está vigente?» | Búsqueda + MCP, con [F] y [T] | «dos días por semana… DOC-1002 está en revisión [F1] [T1]» | [A4](../evidencias/capturas_app/A4_remoto_y_vigencia.png) |
| A5 | «Escríbeme un poema sobre el mar» | `rechazar` | Primera prueba: escribió el poema (falla). Tras el ajuste `agente_v4_app`: «Solicitud no permitida» | [A5](../evidencias/capturas_app/A5_H3_rechazo_tras_reinicio.png) |
| A6 | «¿El DOC-1001 está vigente?» con la casilla de caída del MCP | `ERROR_TECNICO`, sin respuesta inventada | «Error técnico», 1 operación, sin estado inventado | [A6](../evidencias/capturas_app/A3_A6_H1_aclarar_falla_mcp.png) |
| H1 | Preguntas, «Nueva conversación», otra pregunta | Dos conversaciones en la lista | Dos conversaciones, cada una con sus mensajes | [H1](../evidencias/capturas_app/A3_A6_H1_aclarar_falla_mcp.png) |
| H2 | Cerrar sesión y volver a ingresar con la cuenta 1 | Las conversaciones siguen ahí | Siguen las dos conversaciones | Verificado por el equipo |
| H3 | Reiniciar Colab (nuevo enlace) e ingresar | Las conversaciones siguen ahí | La primera conversación cargó con todos sus mensajes | [H3](../evidencias/capturas_app/A5_H3_rechazo_tras_reinicio.png) |
| H4 | Ingresar con la segunda cuenta | No ve las conversaciones de la primera | Lista vacía; solo ve la conversación que creó, con respuesta «dos días hábiles [F1]» | [H4](../evidencias/capturas_app/H4_usuario2_aislado.png) |
| H5 | En Supabase, conversaciones y mensajes por cuenta | Filas con el `usuario_id` de cada cuenta | usuario1: 2 conversaciones, 22 mensajes; usuario2: 1 conversación, 2 mensajes | [H5](../evidencias/capturas_app/H5_filas_por_usuario_supabase.png) |
| D1 | Pruebas desde una URL pública | Igual que en local | Todas las pruebas A y H se hicieron desde la URL pública temporal de Gradio; no hay URL permanente (ver Despliegue) | Esta tabla |

Ajustes hechos por estas pruebas: el poema (A5) y la primera versión de A4, que pidió el código en vez de buscar, se corrigieron en `agente_v4_app` con sus pruebas automáticas; un «Error técnico» intermitente en A4 se atribuyó a los límites de Groq y se agregaron reintentos (sin registro del error en esa ejecución, que ahora se imprime en la consola).

Las métricas que justifican la recuperación elegida están en la [evaluación de la Clase 09](../evidencias/) y en el notebook consolidado: en desarrollo, Recall@3 0,812 (semántica), 0,875 (híbrida) y 0,938 (híbrida con reranking, la elegida); MRR 0,688, 0,729 y 0,875.

## Seguridad, problemas frecuentes y limitaciones

**Seguridad.** Los secretos viven en `app/.env` o en el panel del alojamiento. La aplicación rechaza claves que no sean `sb_publishable_`. Cada solicitud usa la identidad validada por Supabase Auth y RLS repite el control de propietario en la base de datos. El historial es privado de cada cuenta; el corpus solo lo leen las cuentas autorizadas.

| Problema | Qué revisar |
|---|---|
| `Falta la variable ...` al arrancar | `app/.env` o las variables del alojamiento. |
| «No pudimos iniciar sesión» | Que la cuenta exista en Supabase Auth y esté confirmada. |
| Estado «Cuenta sin acceso al corpus» | `CORPUS_ID` y `CORPUS_PROPIETARIO_ID`, y que la cuenta esté en `buscador_corpus_lectores`. |
| «No pudimos guardar o recuperar la conversación» | Que se haya ejecutado `historial.sql`. |
| La aplicación se cierra al cargar modelos | Falta de memoria del alojamiento (ver Despliegue). |
| `ERROR_TECNICO` en consultas de vigencia | `app/mcp.log`. |

**Limitaciones.** Corpus pequeño (9 fragmentos) y ficticio. Cada turno admite 3 decisiones, 2 operaciones y 90 segundos. El modelo puede pedir una aclaración innecesaria o equivocarse al interpretar un plazo; por eso la respuesta siempre muestra su fuente. Las métricas miden la recuperación, no la fidelidad de la respuesta, que sigue requiriendo revisión humana. La primera pregunta tras arrancar es más lenta porque carga el corpus. El enlace de Colab es temporal y no sustituye el despliegue.

## Equipo y referencias

| Integrante | Componentes |
|---|---|
| Joan Sebastián Sosa Bedoya | Cuenta de Supabase con el corpus del proyecto, revisión de respuestas frente a las políticas, pruebas con la segunda cuenta. |
| Alejandra Mejía Patiño | Integración de la aplicación, ejecución y pruebas, documentación. |

Documentos ficticios creados para el curso. Referencias: [Gradio, estado de sesión](https://www.gradio.app/guides/state-in-blocks); [Supabase, Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security); [Supabase, usuario a partir del token](https://supabase.com/docs/reference/python/auth-getuser); [MCP Python SDK](https://py.sdk.modelcontextprotocol.io/); [Groq, Structured Outputs](https://console.groq.com/docs/structured-outputs); [Hugging Face Spaces con Gradio](https://huggingface.co/docs/hub/spaces-sdks-gradio); [Render, Web Services](https://render.com/docs/web-services); [Kotaemon](https://github.com/Cinnamon/kotaemon) como referencia de interfaz.
