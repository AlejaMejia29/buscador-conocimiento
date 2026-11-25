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


_TEXTO, _SUAVE = "#E9ECFF", "#A6AEDB"
_VALORES = dict(
    body_background_fill="transparent", body_text_color=_TEXTO, body_text_color_subdued=_SUAVE,
    background_fill_primary="rgba(16, 20, 48, 0.55)", background_fill_secondary="rgba(255, 255, 255, 0.04)",
    block_background_fill="rgba(16, 20, 48, 0.55)", block_border_color="rgba(160, 170, 255, 0.18)",
    block_border_width="1px", block_shadow="none", border_color_primary="rgba(160, 170, 255, 0.18)",
    block_label_text_color=_SUAVE, block_label_background_fill="transparent",
    block_title_text_color=_SUAVE, block_title_background_fill="transparent",
    button_primary_background_fill="linear-gradient(135deg, #7C3AED, #2563EB)",
    button_primary_background_fill_hover="linear-gradient(135deg, #8B5CF6, #3B82F6)",
    button_primary_text_color="#FFFFFF", button_primary_border_color="transparent",
    button_secondary_background_fill="rgba(255, 255, 255, 0.07)",
    button_secondary_background_fill_hover="rgba(255, 255, 255, 0.14)",
    button_secondary_border_color="rgba(160, 170, 255, 0.25)", button_secondary_text_color=_TEXTO,
    input_background_fill="rgba(6, 8, 24, 0.55)", input_border_color="rgba(160, 170, 255, 0.25)",
    input_placeholder_color="#7F88B8", color_accent_soft="rgba(124, 58, 237, 0.25)",
    link_text_color="#7DD3FC", panel_background_fill="transparent",
)
TEMA = gr.themes.Soft(
    primary_hue="violet", secondary_hue="cyan", neutral_hue="slate", radius_size="lg",
    font=[gr.themes.GoogleFont("Public Sans"), "system-ui", "sans-serif"],
).set(**_VALORES, **{k + "_dark": v for k, v in _VALORES.items()})

CSS = """
body { background: #04050d !important;
  background-image: radial-gradient(ellipse 60% 50% at 12% 8%, rgba(124, 58, 237, .30), transparent 70%),
                    radial-gradient(ellipse 50% 45% at 88% 18%, rgba(14, 165, 233, .20), transparent 70%),
                    radial-gradient(ellipse 70% 50% at 50% 110%, rgba(236, 72, 153, .16), transparent 70%) !important;
  background-attachment: fixed !important; }
gradio-app, .gradio-app, .main, .wrap { background: transparent !important; }
#cielo { position: fixed; inset: 0; width: 100vw; height: 100vh; z-index: 0; pointer-events: none; }
.gradio-container { position: relative; z-index: 1; width: 100% !important; max-width: 1180px !important;
  margin: 0 auto !important; padding: 24px 20px !important; background: transparent !important; perspective: 1400px; }
footer { display: none !important; }
.gradio-container, .gradio-container p, .gradio-container span, .gradio-container label { color: #E9ECFF; }

#encabezado, #encabezado * { overflow: visible !important; }
#encabezado { position: relative; padding: 8px 4px 18px 92px; margin-bottom: 10px; min-height: 76px;
  border-bottom: 1px solid rgba(160, 170, 255, .18); background: transparent !important; border-width: 0 0 1px 0 !important; }
#encabezado h1 { font-size: 30px; margin: 0 0 4px; letter-spacing: -0.01em;
  background: linear-gradient(90deg, #FFFFFF, #C4B5FD 45%, #7DD3FC); -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; }
#encabezado p { color: #A6AEDB; margin: 0; font-size: 15px; }
#encabezado::before { content: ""; position: absolute; left: 12px; top: 8px; width: 56px; height: 56px; border-radius: 50%;
  background: radial-gradient(circle at 32% 28%, #F5D0FE 0%, #A78BFA 28%, #6D28D9 58%, #1E1B4B 100%);
  box-shadow: inset -9px -8px 16px rgba(0, 0, 20, .65), 0 0 28px rgba(139, 92, 246, .55); animation: planeta 7s ease-in-out infinite alternate; translate: calc(var(--px, 0) * 16px) calc(var(--py, 0) * 12px); }
#encabezado::after { content: ""; position: absolute; left: -2px; top: 26px; width: 92px; height: 20px; border-radius: 50%;
  border: 2px solid rgba(196, 181, 253, .55); border-top-color: rgba(196, 181, 253, .15); transform: rotate(-18deg);
  box-shadow: 0 0 14px rgba(167, 139, 250, .35); translate: calc(var(--px, 0) * 16px) calc(var(--py, 0) * 12px); }
@keyframes planeta { from { transform: translateY(0) rotate(0deg); } to { transform: translateY(-5px) rotate(3deg); } }
#encabezado::after { animation-name: anillo; }
@keyframes anillo { from { transform: rotate(-18deg) translateY(0); } to { transform: rotate(-15deg) translateY(-5px); } }

.vidrio, #ingreso, #lateral, #principal, #chat {
  background: rgba(16, 20, 48, .55) !important; border: 1px solid rgba(160, 170, 255, .18) !important;
  backdrop-filter: blur(14px) saturate(140%); -webkit-backdrop-filter: blur(14px) saturate(140%);
  box-shadow: 0 1px 0 rgba(255, 255, 255, .08) inset, 0 18px 40px rgba(0, 0, 20, .55), 0 2px 6px rgba(0, 0, 20, .5); }
#ingreso, #lateral { position: relative; border-radius: 18px !important; transform-style: preserve-3d;
  transform: perspective(900px) rotateX(var(--rx, 0deg)) rotateY(var(--ry, 0deg)); transition: transform .18s ease-out, box-shadow .25s; }
#ingreso:hover, #lateral:hover { box-shadow: 0 1px 0 rgba(255, 255, 255, .1) inset, 0 26px 56px rgba(40, 20, 120, .55), 0 4px 10px rgba(0, 0, 20, .5); }
#ingreso::before, #lateral::before { content: ""; position: absolute; inset: 0; border-radius: inherit; pointer-events: none;
  background: radial-gradient(260px circle at var(--mx, 50%) var(--my, 0%), rgba(167, 139, 250, .22), transparent 70%); opacity: .9; }
#ingreso { max-width: 420px; margin: 40px auto 0 !important; padding: 28px !important; gap: 14px; }
#ingreso .form, #ingreso .block, #lateral .form, #lateral .block { border: none !important; box-shadow: none !important; background: transparent !important; padding: 0 !important; backdrop-filter: none !important; }
#ingreso h2 { font-size: 20px; color: #FFFFFF; margin: 0; }
#barra { align-items: center; padding: 4px 4px 8px; background: transparent !important; border: none !important; box-shadow: none !important; }
#barra p { margin: 0; color: #A6AEDB; }
#barra b { color: #FFFFFF; }
#barra button { max-width: 150px; margin-left: auto; }
#lateral { padding: 14px !important; gap: 12px; align-self: stretch; }
#lista { border: none !important; box-shadow: none !important; padding: 0 !important; background: transparent !important; }
#lista, #lista * { background-color: transparent !important; }
#lista .wrap { flex-direction: column; gap: 8px; }
#lista > span, #lista [data-testid="block-info"] { font-weight: 600; color: #FFFFFF !important; background: transparent !important; padding: 0 !important; }
#lista label { width: 100%; margin: 0; padding: 10px 12px; border-radius: 12px; border: 1px solid rgba(160, 170, 255, .22);
  background-color: rgba(255, 255, 255, .05) !important; font-size: 14px; line-height: 1.35; cursor: pointer;
  transition: transform .15s, background-color .2s, border-color .2s, box-shadow .2s; }
#lista label:hover { transform: translateX(4px) translateZ(0); border-color: rgba(125, 211, 252, .6); box-shadow: 0 6px 18px rgba(14, 165, 233, .2); }
#lista label.selected, #lista label:has(input:checked) { background-color: rgba(124, 58, 237, .28) !important;
  border-color: #A78BFA !important; box-shadow: 0 0 18px rgba(139, 92, 246, .45); }
#lista label span, #lista label.selected span { color: #E9ECFF !important; }
#lista input[type=radio] { display: none; }
#principal { gap: 12px; background: transparent !important; border: none !important; box-shadow: none !important; backdrop-filter: none !important; perspective: 1000px; }
#chat { border-radius: 18px !important; overflow: hidden; }
#chat .placeholder, #chat .placeholder * { color: #A6AEDB !important; }
#chat .message-row { animation: aparece .45s cubic-bezier(.2, .8, .2, 1) both; transform-origin: 50% 100%; }
@keyframes aparece { from { opacity: 0; transform: perspective(700px) rotateX(22deg) translateY(16px) scale(.95); } to { opacity: 1; transform: none; } }
#chat .user.message { background: linear-gradient(135deg, #7C3AED, #3B82F6) !important; color: #FFFFFF !important; border: none !important;
  border-radius: 18px 18px 4px 18px !important; box-shadow: 0 12px 26px rgba(59, 90, 246, .42), 0 2px 4px rgba(0, 0, 20, .4), 0 1px 0 rgba(255, 255, 255, .3) inset; }
#chat .bot.message { background: rgba(255, 255, 255, .08) !important; color: #E9ECFF !important; border: 1px solid rgba(160, 170, 255, .24) !important;
  border-radius: 18px 18px 18px 4px !important; box-shadow: 0 12px 26px rgba(0, 0, 20, .5), 0 1px 0 rgba(255, 255, 255, .12) inset; }
#chat .user.message > .message, #chat .bot.message > .message, #chat [data-testid="user"], #chat [data-testid="bot"] { background: transparent !important; border: none !important; box-shadow: none !important; }
#chat .user.message, #chat .bot.message { transition: transform .2s, box-shadow .2s; }
#chat .user.message:hover, #chat .bot.message:hover { transform: translateY(-3px); }
#chat .user.message:hover { box-shadow: 0 18px 34px rgba(59, 90, 246, .55), 0 2px 4px rgba(0, 0, 20, .4), 0 1px 0 rgba(255, 255, 255, .3) inset; }
#chat .bot.message:hover { box-shadow: 0 18px 34px rgba(0, 0, 20, .6), 0 0 22px rgba(139, 92, 246, .25), 0 1px 0 rgba(255, 255, 255, .12) inset; }
#chat .message-content, #chat .message-content * { color: inherit; }
#chat sub, #chat sub * { color: #A6AEDB !important; }
#entrada { align-items: stretch; gap: 10px; background: transparent !important; border: none !important; box-shadow: none !important; }
#entrada textarea, #entrada input { border-radius: 14px !important; box-shadow: 0 8px 22px rgba(0, 0, 20, .45) inset, 0 0 0 1px rgba(160, 170, 255, .25); color: #E9ECFF !important; }
#entrada textarea:focus { box-shadow: 0 0 0 2px #8B5CF6, 0 0 22px rgba(139, 92, 246, .5) !important; }
button.primary, button.secondary, .gradio-container button { transition: transform .15s, box-shadow .2s, filter .2s; }
button.primary { box-shadow: 0 8px 22px rgba(79, 70, 229, .5), 0 1px 0 rgba(255, 255, 255, .25) inset; }
button.primary:hover { transform: translateY(-2px); box-shadow: 0 14px 30px rgba(99, 102, 241, .65), 0 1px 0 rgba(255, 255, 255, .3) inset; filter: brightness(1.08); }
button.primary:active { transform: translateY(1px) scale(.98); }
#entrada button { min-height: 48px; }
#estado p { color: #A6AEDB; font-size: 13px; margin: 0 4px; }
#fuentes blockquote { border-left: 3px solid #8B5CF6; margin: 6px 0 12px; padding: 4px 12px; color: #C9CFF0; background: rgba(255, 255, 255, .04); border-radius: 0 8px 8px 0; }
.gradio-container .accordion, .gradio-container details { background: rgba(16, 20, 48, .55) !important; border-radius: 14px; }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
@media (max-width: 700px) { #encabezado { padding-left: 84px; } #encabezado h1 { font-size: 24px; } }
"""

HEAD = """
<script>
(function () {
  if (window.__universo) return; window.__universo = true;
  var quieto = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var cv, cx, w = 0, h = 0, dpr = 1, capas = [], fugaces = [], mx = 0, my = 0, tx = 0, ty = 0;
  function crear() {
    cv = document.createElement('canvas'); cv.id = 'cielo'; document.body.prepend(cv); cx = cv.getContext('2d');
    ajustar(); window.addEventListener('resize', ajustar); if (quieto) dibujar(0); else requestAnimationFrame(dibujar);
  }
  function ajustar() {
    dpr = Math.min(window.devicePixelRatio || 1, 2); w = window.innerWidth; h = window.innerHeight;
    cv.width = w * dpr; cv.height = h * dpr; cx.setTransform(dpr, 0, 0, dpr, 0, 0);
    var base = Math.round(w * h / 9000);
    capas = [{ n: base, r: 0.7, v: 0.04, p: 8 }, { n: Math.round(base * .45), r: 1.2, v: 0.09, p: 18 }, { n: Math.round(base * .18), r: 1.9, v: 0.16, p: 34 }]
      .map(function (c) { c.e = []; for (var i = 0; i < c.n; i++) c.e.push({ x: Math.random() * w, y: Math.random() * h, f: Math.random() * 6.28, t: 0.6 + Math.random() * 1.6, c: Math.random() }); return c; });
  }
  function dibujar(t) {
    if (!document.hidden) {
      tx += (mx - tx) * 0.05; ty += (my - ty) * 0.05; cx.clearRect(0, 0, w, h);
      capas.forEach(function (c) {
        c.e.forEach(function (s) {
          if (!quieto) { s.y -= c.v; if (s.y < -2) { s.y = h + 2; s.x = Math.random() * w; } }
          var a = 0.45 + 0.45 * Math.sin(t / 1000 * s.t + s.f), px = s.x + tx * c.p, py = s.y + ty * c.p;
          cx.fillStyle = s.c > 0.8 ? 'rgba(165,180,252,' + a + ')' : s.c > 0.65 ? 'rgba(125,211,252,' + a + ')' : 'rgba(255,255,255,' + a + ')';
          cx.beginPath(); cx.arc(px, py, c.r, 0, 6.283); cx.fill();
        });
      });
      if (!quieto) {
        if (Math.random() < 0.004 && fugaces.length < 2) fugaces.push({ x: Math.random() * w * 0.8 + w * 0.2, y: Math.random() * h * 0.4, vx: -6 - Math.random() * 4, vy: 3 + Math.random() * 2, vida: 1 });
        fugaces = fugaces.filter(function (f) {
          f.x += f.vx; f.y += f.vy; f.vida -= 0.018;
          var g = cx.createLinearGradient(f.x, f.y, f.x - f.vx * 9, f.y - f.vy * 9);
          g.addColorStop(0, 'rgba(255,255,255,' + f.vida + ')'); g.addColorStop(1, 'rgba(125,211,252,0)');
          cx.strokeStyle = g; cx.lineWidth = 1.6; cx.beginPath(); cx.moveTo(f.x, f.y); cx.lineTo(f.x - f.vx * 9, f.y - f.vy * 9); cx.stroke();
          return f.vida > 0;
        });
      }
    }
    if (!quieto) requestAnimationFrame(dibujar);
  }
  document.addEventListener('mousemove', function (e) {
    mx = e.clientX / window.innerWidth - 0.5; my = e.clientY / window.innerHeight - 0.5;
    document.documentElement.style.setProperty('--px', mx.toFixed(3)); document.documentElement.style.setProperty('--py', my.toFixed(3));
    var p = e.target.closest && e.target.closest('#ingreso, #lateral');
    document.querySelectorAll('#ingreso, #lateral').forEach(function (el) {
      if (el !== p) { el.style.setProperty('--rx', '0deg'); el.style.setProperty('--ry', '0deg'); }
    });
    if (p && !quieto) {
      var r = p.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
      p.style.setProperty('--ry', ((x - 0.5) * 7).toFixed(2) + 'deg'); p.style.setProperty('--rx', ((0.5 - y) * 7).toFixed(2) + 'deg');
      p.style.setProperty('--mx', (x * 100).toFixed(1) + '%'); p.style.setProperty('--my', (y * 100).toFixed(1) + '%');
    }
  }, { passive: true });
  if (document.body) crear(); else document.addEventListener('DOMContentLoaded', crear);
})();
</script>
"""


def construir_interfaz(sistema: Sistema, almacen: Almacenamiento) -> gr.Blocks:
    with gr.Blocks(title="Buscador de conocimiento") as demo:
        sesion = gr.State(None)          # Sesion de Supabase Auth de este navegador
        conversacion = gr.State(None)    # id de la conversación activa

        gr.Markdown("# Buscador de conocimiento\nPreguntas sobre las políticas internas, con la fuente de cada respuesta.",
                    elem_id="encabezado")

        with gr.Column(visible=True, elem_id="ingreso") as panel_ingreso:
            gr.Markdown("## Ingresar")
            correo = gr.Textbox(label="Correo", max_lines=1, placeholder="nombre@correo.com")
            contrasena = gr.Textbox(label="Contraseña", type="password", max_lines=1)
            boton_ingresar = gr.Button("Ingresar", variant="primary")
            aviso_ingreso = gr.Markdown()

        with gr.Column(visible=False) as panel_chat:
            with gr.Row(elem_id="barra"):
                usuario_activo = gr.Markdown()
                boton_salir = gr.Button("Cerrar sesión", size="sm", scale=0, min_width=130)
            with gr.Row(equal_height=False):
                with gr.Column(scale=1, min_width=240, elem_id="lateral"):
                    boton_nueva = gr.Button("＋ Nueva conversación", variant="primary")
                    lista = gr.Radio(label="Mis conversaciones", choices=[], value=None, elem_id="lista")
                with gr.Column(scale=3, elem_id="principal"):
                    chat = gr.Chatbot(label="Conversación", height=480, elem_id="chat", show_label=False,
                                      placeholder="Escribe una pregunta sobre vacaciones, permisos, trabajo remoto o incapacidades.")
                    with gr.Row(elem_id="entrada"):
                        pregunta = gr.Textbox(placeholder="Ej.: ¿Con cuánta anticipación pido vacaciones?",
                                              show_label=False, max_lines=4, scale=5, container=False)
                        boton_enviar = gr.Button("Enviar", variant="primary", scale=1, min_width=110)
                    simular = gr.Checkbox(label="Prueba: simular caída del servidor MCP",
                                          value=False, visible=sistema.cfg.modo_pruebas, container=False)
                    estado = gr.Markdown(elem_id="estado")
                    with gr.Accordion("Fuentes de la última respuesta", open=False):
                        fuentes = gr.Markdown(elem_id="fuentes")

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
                    f"Sesión de <b>{nueva.correo.replace('@', '&#64;')}</b>")

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
        theme=TEMA, css=CSS, head=HEAD,
    )


if __name__ == "__main__":
    main()
