"""Sesiones de Supabase Auth e historial de conversaciones en Supabase.

Reemplaza el diccionario MEMORIA de la Clase 11. Cada operación crea un cliente nuevo con
la sesión del usuario que hace la solicitud, valida su token con Supabase Auth y comprueba
que la conversación le pertenezca antes de leer o escribir. Además, las políticas RLS de
supabase/historial.sql repiten esa comprobación en la base de datos.
Nunca se comparte entre usuarios un cliente autenticado.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from supabase import ClientOptions, create_client

PATRON_UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


class ErrorSesion(Exception):
    """La sesión no existe, expiró sin poder renovarse o las credenciales no son válidas."""


class AccesoDenegado(Exception):
    """La conversación no existe o no pertenece al usuario."""


@dataclass(frozen=True)
class Sesion:
    """Lo único que la interfaz guarda en gr.State. No contiene la contraseña."""
    usuario_id: str
    correo: str
    access_token: str
    refresh_token: str


class Almacenamiento:
    def __init__(self, supabase_url: str, supabase_publishable_key: str):
        self.url = supabase_url
        self.clave = supabase_publishable_key

    def _cliente_nuevo(self):
        return create_client(self.url, self.clave,
                             options=ClientOptions(persist_session=False, auto_refresh_token=False))

    # -- Identidad -----------------------------------------------------------
    def iniciar_sesion(self, correo: str, contrasena: str) -> Sesion:
        correo = (correo or "").strip()
        if not correo or not contrasena:
            raise ErrorSesion("Escribe tu correo y tu contraseña.")
        cliente = self._cliente_nuevo()
        try:
            respuesta = cliente.auth.sign_in_with_password({"email": correo, "password": contrasena})
        except Exception:
            raise ErrorSesion("No pudimos iniciar sesión. Revisa el correo y la contraseña.") from None
        if respuesta.user is None or respuesta.session is None:
            raise ErrorSesion("Supabase no devolvió una sesión válida.")
        return Sesion(respuesta.user.id, respuesta.user.email or correo,
                      respuesta.session.access_token, respuesta.session.refresh_token)

    def cliente(self, sesion: Sesion | None):
        """Cliente de Supabase con la identidad de esta sesión.

        set_session valida el token con Supabase Auth (o lo renueva si expiró), así que el
        usuario_id sale del servidor de autenticación y no de lo que guarda el navegador.
        Devuelve el cliente y la sesión vigente, que la interfaz vuelve a guardar en gr.State.
        """
        if sesion is None:
            raise ErrorSesion("Inicia sesión para continuar.")
        cliente = self._cliente_nuevo()
        try:
            respuesta = cliente.auth.set_session(sesion.access_token, sesion.refresh_token)
        except Exception:
            raise ErrorSesion("Tu sesión expiró. Vuelve a iniciar sesión.") from None
        if respuesta is None or respuesta.user is None or respuesta.session is None:
            raise ErrorSesion("Tu sesión expiró. Vuelve a iniciar sesión.")
        vigente = Sesion(respuesta.user.id, respuesta.user.email or sesion.correo,
                         respuesta.session.access_token, respuesta.session.refresh_token)
        return cliente, vigente

    def cerrar_sesion(self, sesion: Sesion | None):
        if sesion is None:
            return
        try:
            cliente, _ = self.cliente(sesion)
            cliente.auth.sign_out()
        except Exception:
            pass   # si ya expiró, no hay nada que cerrar

    # -- Conversaciones -----------------------------------------------------
    def crear_conversacion(self, cliente, sesion: Sesion, titulo: str) -> dict:
        titulo = re.sub(r"\s+", " ", titulo or "").strip()[:120] or "Conversación nueva"
        fila = (cliente.table("buscador_conversaciones")
                .insert({"usuario_id": sesion.usuario_id, "titulo": titulo})
                .execute().data)
        if len(fila) != 1 or fila[0]["usuario_id"] != sesion.usuario_id:
            raise RuntimeError("Supabase no confirmó la conversación nueva.")
        return fila[0]

    def listar_conversaciones(self, cliente, sesion: Sesion) -> list[dict]:
        return (cliente.table("buscador_conversaciones").select("id,titulo,creada_en")
                .eq("usuario_id", sesion.usuario_id)
                .order("creada_en", desc=True).limit(100).execute().data)

    def comprobar_propietario(self, cliente, sesion: Sesion, conversacion_id: str) -> dict:
        if not isinstance(conversacion_id, str) or not re.fullmatch(PATRON_UUID, conversacion_id):
            raise AccesoDenegado("Identificador de conversación no válido.")
        filas = (cliente.table("buscador_conversaciones").select("id,usuario_id,titulo")
                 .eq("id", conversacion_id).eq("usuario_id", sesion.usuario_id)
                 .limit(1).execute().data)
        if not filas:
            # RLS oculta las conversaciones ajenas: para el usuario no existen.
            raise AccesoDenegado("La conversación no existe o no te pertenece.")
        return filas[0]

    def renombrar_si_es_nueva(self, cliente, sesion: Sesion, conversacion: dict, primera_pregunta: str):
        if conversacion.get("titulo") != "Conversación nueva":
            return conversacion
        titulo = re.sub(r"\s+", " ", primera_pregunta).strip()[:60] or "Conversación nueva"
        filas = (cliente.table("buscador_conversaciones").update({"titulo": titulo})
                 .eq("id", conversacion["id"]).eq("usuario_id", sesion.usuario_id).execute().data)
        return filas[0] if filas else conversacion

    # -- Mensajes -------------------------------------------------------------
    def cargar_mensajes(self, cliente, sesion: Sesion, conversacion_id: str) -> list[dict]:
        self.comprobar_propietario(cliente, sesion, conversacion_id)
        return (cliente.table("buscador_mensajes")
                .select("id,rol,contenido,estado,fuentes,creado_en")
                .eq("conversacion_id", conversacion_id).eq("usuario_id", sesion.usuario_id)
                .order("id").limit(1000).execute().data)

    def guardar_turno(self, cliente, sesion: Sesion, conversacion_id: str, pregunta: str,
                      respuesta: str, estado: str, fuentes: list[dict]) -> list[dict]:
        """Guarda la pregunta y la respuesta del turno. Devuelve las filas confirmadas por Supabase."""
        self.comprobar_propietario(cliente, sesion, conversacion_id)
        filas = [
            {"conversacion_id": conversacion_id, "usuario_id": sesion.usuario_id, "rol": "usuario",
             "contenido": pregunta[:6000], "estado": None, "fuentes": []},
            {"conversacion_id": conversacion_id, "usuario_id": sesion.usuario_id, "rol": "asistente",
             "contenido": (respuesta or "Sin respuesta.")[:6000], "estado": estado, "fuentes": fuentes},
        ]
        guardadas = cliente.table("buscador_mensajes").insert(filas).execute().data
        if len(guardadas) != 2:
            raise RuntimeError("Supabase no confirmó el guardado del turno.")
        return guardadas


def historial_para_modelo(mensajes: list[dict], max_turnos: int) -> list[dict]:
    """Convierte los mensajes guardados en los turnos {usuario, respuesta} que usa el agente.

    Se guardan todos los mensajes, pero al modelo solo le enviamos los últimos max_turnos
    turnos completos, como la ventana de memoria de la Clase 11.
    """
    turnos, pregunta = [], None
    for m in mensajes:
        if m["rol"] == "usuario":
            pregunta = m["contenido"]
        elif m["rol"] == "asistente" and pregunta is not None:
            turnos.append({"usuario": pregunta, "respuesta": m["contenido"]})
            pregunta = None
    return turnos[-max_turnos:]
