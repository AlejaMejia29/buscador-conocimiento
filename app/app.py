"""Interfaz web del Buscador de conocimiento (Gradio).

Recibe la pregunta, gestiona el estado de cada sesión del navegador y muestra respuesta,
fuentes y estado. No repite la lógica del proyecto: llama a sistema.py para atender la
pregunta y a almacenamiento.py para la identidad y el historial en Supabase.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

import gradio as gr
from dotenv import load_dotenv

from almacenamiento import AccesoDenegado, Almacenamiento, ErrorSesion, historial_para_modelo
from sistema import MAX_TURNOS, Configuracion, Sistema, fuentes_citadas

load_dotenv(Path(__file__).resolve().parent / ".env")

ETIQUETAS_ESTADO = {
    "RESPONDER": "Respuesta con fuentes",
    "ACLARAR": "Necesita una aclaración",
    "RECHAZAR": "Solicitud no permitida",
    "SIN_ACCESO_CORPUS": "Cuenta sin acceso al corpus",
    "SIN_EVIDENCIA_DOCUMENTAL": "Sin evidencia en los documentos",
    "ERROR_VALIDACION": "Falló un control de validación",
    "ERROR_TECNICO": "Error técnico",
    "LIMITE_TIEMPO": "Tiempo de espera agotado",
}


def texto_fuentes(fuentes):
    if not fuentes:
        return "_Esta respuesta no usó fuentes documentales ni herramientas._"
    lineas = []
    for f in fuentes:
        if f["tipo"] == "pasaje":
            lineas.append(f"**[{f['etiqueta']}] {f['documento']} ({f['codigo']}) · {f['seccion']}** · versión {f['version']}\n\n"
                          f"> {f['texto'].replace(chr(10), ' ')}")
        else:
            registro = f.get("registro") or {}
            detalle = (f"{registro.get('nombre')}: **{registro.get('estado')}**. {registro.get('detalle')}"
                       if f.get("encontrada") else "El código no existe en el registro de vigencia.")
            lineas.append(f"**[{f['etiqueta']}] Herramienta MCP `consultar_estado_documento` · {f['codigo']}**\n\n> {detalle}")
    return "\n\n".join(lineas)


def a_chatbot(mensajes):
    """Mensajes guardados en Supabase → formato de gr.Chatbot."""
    salida = []
    for m in mensajes:
        if m["rol"] == "usuario":
            salida.append({"role": "user", "content": m["contenido"]})
        else:
            contenido = m["contenido"]
            etiquetas = [f"[{f['etiqueta']}] {f.get('documento') or 'MCP ' + str(f.get('codigo'))}" for f in (m.get("fuentes") or [])]
            pie = ETIQUETAS_ESTADO.get(m.get("estado") or "", m.get("estado") or "")
            if etiquetas:
                pie += " · Fuentes: " + "; ".join(etiquetas)
            salida.append({"role": "assistant", "content": f"{contenido}\n\n<sub>{pie}</sub>" if pie else contenido})
    return salida


def opciones_conversaciones(conversaciones):
    return [(c["titulo"], c["id"]) for c in conversaciones]


def construir_interfaz(sistema: Sistema, almacen: Almacenamiento) -> gr.Blocks:
    with gr.Blocks(title="Buscador de conocimiento") as demo:
        sesion = gr.State(None)          # Sesion de Supabase Auth de este navegador
        conversacion = gr.State(None)    # id de la conversación activa

        gr.Markdown("# Buscador de conocimiento\nPreguntas sobre las políticas internas, con la fuente de cada respuesta.")

        with gr.Column(visible=True) as panel_ingreso:
            correo = gr.Textbox(label="Correo", max_lines=1)
            contrasena = gr.Textbox(label="Contraseña", type="password", max_lines=1)
            boton_ingresar = gr.Button("Ingresar", variant="primary")
            aviso_ingreso = gr.Markdown()

        with gr.Column(visible=False) as panel_chat:
            with gr.Row():
                usuario_activo = gr.Markdown()
                boton_salir = gr.Button("Cerrar sesión", size="sm", scale=0)
            with gr.Row():
                with gr.Column(scale=1, min_width=220):
                    boton_nueva = gr.Button("Nueva conversación")
                    lista = gr.Radio(label="Mis conversaciones", choices=[], value=None)
                with gr.Column(scale=3):
                    chat = gr.Chatbot(label="Conversación", height=460)
                    with gr.Row():
                        pregunta = gr.Textbox(placeholder="Ej.: ¿Con cuánta anticipación pido vacaciones?",
                                              show_label=False, max_lines=4, scale=5)
                        boton_enviar = gr.Button("Enviar", variant="primary", scale=1)
                    simular = gr.Checkbox(label="Prueba: simular caída del servidor MCP",
                                          value=False, visible=sistema.cfg.modo_pruebas)
                    estado = gr.Markdown()
                    with gr.Accordion("Fuentes de la última respuesta", open=True):
                        fuentes = gr.Markdown()

        def salir_ui(mensaje=""):
            return (None, None, gr.update(visible=True), gr.update(visible=False), mensaje,
                    gr.update(choices=[], value=None), [], "", "")

        salidas_ingreso = [sesion, conversacion, panel_ingreso, panel_chat, aviso_ingreso, lista, chat, fuentes, estado]

        async def ingresar(correo_txt, contrasena_txt):
            try:
                nueva = await asyncio.to_thread(almacen.iniciar_sesion, correo_txt, contrasena_txt)
                cliente, nueva = await asyncio.to_thread(almacen.cliente, nueva)
                conversaciones = await asyncio.to_thread(almacen.listar_conversaciones, cliente, nueva)
            except ErrorSesion as error:
                return (*salir_ui(f"⚠️ {error}"), gr.update(), f"")
            return (nueva, None, gr.update(visible=False), gr.update(visible=True), "",
                    gr.update(choices=opciones_conversaciones(conversaciones), value=None), [], "",
                    "Escribe una pregunta para empezar una conversación nueva.", "",
                    f"Sesión de **{nueva.correo}**")

        boton_ingresar.click(ingresar, [correo, contrasena], [*salidas_ingreso, contrasena, usuario_activo])
        contrasena.submit(ingresar, [correo, contrasena], [*salidas_ingreso, contrasena, usuario_activo])

        async def salir(sesion_actual):
            await asyncio.to_thread(almacen.cerrar_sesion, sesion_actual)
            return salir_ui("Cerraste sesión.")

        boton_salir.click(salir, [sesion], salidas_ingreso)

        def nueva_conversacion():
            return None, gr.update(value=None), [], "", "Conversación nueva: escribe tu primera pregunta."

        boton_nueva.click(nueva_conversacion, None, [conversacion, lista, chat, fuentes, estado])

        async def abrir(conversacion_id, sesion_actual):
            if not conversacion_id:
                return gr.update(), conversacion_id, gr.update(), gr.update(), gr.update()
            try:
                cliente, sesion_actual = await asyncio.to_thread(almacen.cliente, sesion_actual)
                mensajes = await asyncio.to_thread(almacen.cargar_mensajes, cliente, sesion_actual, conversacion_id)
            except ErrorSesion as error:
                return None, None, [], "", f"⚠️ {error} Cierra sesión y vuelve a ingresar."
            except AccesoDenegado as error:
                return sesion_actual, None, [], "", f"⚠️ {error}"
            ultima = next((m for m in reversed(mensajes) if m["rol"] == "asistente"), None)
            return (sesion_actual, conversacion_id, a_chatbot(mensajes),
                    texto_fuentes(ultima["fuentes"]) if ultima else "", f"{len(mensajes)} mensajes recuperados de Supabase.")

        lista.input(abrir, [lista, sesion], [sesion, conversacion, chat, fuentes, estado])

        async def enviar(texto, sesion_actual, conversacion_id, simular_fallo):
            texto = (texto or "").strip()
            if not texto:
                return texto, sesion_actual, conversacion_id, gr.update(), gr.update(), gr.update(), "Escribe una pregunta."
            try:
                cliente, sesion_actual = await asyncio.to_thread(almacen.cliente, sesion_actual)
                if conversacion_id is None:
                    actual = await asyncio.to_thread(almacen.crear_conversacion, cliente, sesion_actual, texto[:60])
                    conversacion_id = actual["id"]
                    mensajes = []
                else:
                    mensajes = await asyncio.to_thread(almacen.cargar_mensajes, cliente, sesion_actual, conversacion_id)
                historial = historial_para_modelo(mensajes, MAX_TURNOS)
                traza = await sistema.atender(texto, cliente, historial,
                                              simular_fallo_mcp=bool(simular_fallo) and sistema.cfg.modo_pruebas)
                citadas = fuentes_citadas(traza)
                await asyncio.to_thread(almacen.guardar_turno, cliente, sesion_actual, conversacion_id,
                                        texto, traza["respuesta"], traza["estado"], citadas)
                # Mostramos lo que quedó guardado, no lo que tenemos en memoria.
                mensajes = await asyncio.to_thread(almacen.cargar_mensajes, cliente, sesion_actual, conversacion_id)
                conversaciones = await asyncio.to_thread(almacen.listar_conversaciones, cliente, sesion_actual)
            except ErrorSesion as error:
                return texto, None, None, [], gr.update(choices=[], value=None), "", f"⚠️ {error} Vuelve a iniciar sesión."
            except AccesoDenegado as error:
                return texto, sesion_actual, None, [], gr.update(), "", f"⚠️ {error}"
            except ValueError as error:
                return texto, sesion_actual, conversacion_id, gr.update(), gr.update(), gr.update(), f"⚠️ {error}"
            except Exception as error:
                return (texto, sesion_actual, conversacion_id, gr.update(), gr.update(), gr.update(),
                        f"⚠️ No pudimos guardar o recuperar la conversación ({type(error).__name__}). No se guardó este turno.")
            detalle = f"**{ETIQUETAS_ESTADO.get(traza['estado'], traza['estado'])}** · {traza['operaciones']} operaciones · {traza['duracion_ms']:.0f} ms · guardado en Supabase"
            return ("", sesion_actual, conversacion_id, a_chatbot(mensajes),
                    gr.update(choices=opciones_conversaciones(conversaciones), value=conversacion_id),
                    texto_fuentes(citadas), detalle)

        salidas_envio = [pregunta, sesion, conversacion, chat, lista, fuentes, estado]
        boton_enviar.click(enviar, [pregunta, sesion, conversacion, simular], salidas_envio)
        pregunta.submit(enviar, [pregunta, sesion, conversacion, simular], salidas_envio)

    return demo


def main():
    cfg = Configuracion.desde_entorno()
    print("Preparando modelos y servidor MCP (solo una vez)...")
    sistema = Sistema.preparar(cfg)
    almacen = Almacenamiento(cfg.supabase_url, cfg.supabase_publishable_key)
    demo = construir_interfaz(sistema, almacen)
    demo.queue(default_concurrency_limit=4).launch(
        server_name=os.environ.get("GRADIO_SERVER_NAME", "127.0.0.1"),
        server_port=int(os.environ.get("PORT", "7860")),
        share=os.environ.get("GRADIO_SHARE", "0") == "1",
    )


if __name__ == "__main__":
    main()
