"""Pruebas sin claves: servidor MCP real, contratos, controles del agente e historial.

Se ejecutan desde app/ con:  python -m pytest pruebas -q
No llaman a Groq ni a Supabase; esas pruebas se hacen desde la aplicación (ver README).
"""
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from almacenamiento import AccesoDenegado, Almacenamiento, Sesion, historial_para_modelo  # noqa: E402
from sistema import (MAX_OPERACIONES, ClienteMCP, Configuracion, Decision, Detencion, Sistema,  # noqa: E402
                     codigos_permitidos, controlar_operacion, falta_evidencia_documental,
                     fuentes_citadas, fusionar_rrf, validar_decision)

CFG = Configuracion(groq_api_key="x", groq_model="openai/gpt-oss-20b",
                    supabase_url="https://ejemplo.supabase.co", supabase_publishable_key="sb_publishable_x",
                    corpus_id="buscador_conocimiento-29dccc23ac01",
                    corpus_propietario_id="00000000-0000-0000-0000-000000000000",
                    embeddings_revision="e8f8c211226b894fcb81acc59f3b34ba3efd5f42")


def decision(**campos):
    base = {"accion": "responder", "consulta": "", "codigo_documento": "", "respuesta": "", "citas": []}
    return Decision(**{**base, **campos})


# --- MCP real por stdio ----------------------------------------------------------
def test_mcp_catalogo_y_consultas():
    async def recorrido():
        mcp = ClienteMCP(registro=Path("mcp_pruebas.log"))
        catalogo = await mcp.descubrir()
        assert catalogo["nombre"] == "consultar_estado_documento"
        vigente = await mcp.consultar_estado("DOC-1001")
        assert vigente["encontrada"] and vigente["registro"]["estado"] == "vigente"
        desconocido = await mcp.consultar_estado("DOC-9999")
        assert desconocido["encontrada"] is False and desconocido["registro"] is None
        async with mcp.conexion() as conexion:
            invalida = await conexion.call_tool("consultar_estado_documento", {"codigo_documento": "1001"})
            assert invalida.is_error
        with pytest.raises(ConnectionError):
            await mcp.consultar_estado("DOC-1001", simular_fallo=True)
    asyncio.run(recorrido())
    Path("mcp_pruebas.log").unlink(missing_ok=True)


# --- Contratos y controles -------------------------------------------------------
def test_codigo_debe_venir_del_usuario():
    assert codigos_permitidos("¿Y ese documento?", []) == set()
    assert codigos_permitidos("Ahora DOC-1002", [{"usuario": "Antes DOC-1001"}]) == {"DOC-1002"}
    with pytest.raises(ValueError):
        validar_decision(decision(accion="consultar_estado_documento", codigo_documento="DOC-1003"),
                         "¿Está vigente mi documento?", [], {})


def test_citas_normalizadas_e_inexistentes():
    normal = validar_decision(decision(respuesta="Se piden con 15 días [F1, F2].", citas=["[F1]", "F2"]),
                              "vacaciones", [], {"F1": {}, "F2": {}})
    assert normal.citas == ["F1", "F2"]
    with pytest.raises(ValueError):
        validar_decision(decision(respuesta="Dato [F7].", citas=["F7"]), "vacaciones", [], {"F1": {}})


def test_no_responde_sobre_politicas_sin_fuente():
    sin_fuente = decision(respuesta="No hay límite de días remotos.")
    assert falta_evidencia_documental(sin_fuente, "¿Hay límite de días de trabajo remoto?", {})
    assert not falta_evidencia_documental(decision(respuesta="¡Hola!"), "Hola", {})


def test_limites_y_repeticion():
    visitadas = set()
    controlar_operacion("consultar_estado_documento", {"codigo_documento": "DOC-1001"}, visitadas, 0)
    with pytest.raises(Detencion, match="REPETICION_SIN_AVANCE"):
        controlar_operacion("consultar_estado_documento", {"codigo_documento": "DOC-1001"}, visitadas, 1)
    with pytest.raises(Detencion, match="LIMITE_OPERACIONES"):
        controlar_operacion("buscar_documentos", {"consulta": "vacaciones"}, visitadas, MAX_OPERACIONES)


def test_rrf():
    fusion = fusionar_rrf([{"chunk_id": x} for x in "ABC"], [{"chunk_id": x} for x in "CAD"])
    assert [r["chunk_id"] for r in fusion] == ["A", "C", "B", "D"]


def test_configuracion_rechaza_clave_administrativa():
    with pytest.raises(ValueError):
        Configuracion(**{**CFG.__dict__, "supabase_publishable_key": "sb_secret_x"}).validar()
    CFG.validar()


# --- Recorrido del agente con un modelo simulado ----------------------------------
class RecuperadorFalso:
    def buscar(self, consulta, cliente):
        return [{"chunk_id": "Politica_Permisos:1.0-ficticio:parrafos:2", "texto": "Trabajo remoto: hasta dos días.",
                 "fuente": {"source": "Politica_Permisos.md", "codigo": "DOC-1002", "section": "Trabajo remoto",
                            "version": "1.0-ficticio", "source_hash": "x"}, "puntaje_reranker": 3.2}]


def sistema_con(decisiones):
    s = Sistema(cfg=CFG, recuperador=RecuperadorFalso())
    s.mcp.catalogo = {"nombre": "consultar_estado_documento"}
    pendientes = list(decisiones)

    async def decidir(texto, historial, observaciones):
        return pendientes.pop(0), None
    s.decidir = decidir
    return s


def test_recorrido_buscar_y_responder():
    s = sistema_con([decision(accion="buscar_documentos", consulta="trabajo remoto"),
                     decision(respuesta="Hasta dos días [F1].", citas=["F1"])])
    traza = asyncio.run(s.atender("¿Cuántos días puedo trabajar desde casa?", cliente_supabase=None, historial=[]))
    assert traza["estado"] == "RESPONDER" and traza["citas"] == ["F1"]
    assert fuentes_citadas(traza)[0]["documento"] == "Politica_Permisos.md"


def test_respuesta_sin_buscar_se_bloquea():
    s = sistema_con([decision(respuesta="No hay límite de días remotos."),
                     decision(respuesta="Sigo sin buscar.")])
    traza = asyncio.run(s.atender("¿Hay límite de trabajo remoto?", cliente_supabase=None, historial=[]))
    assert traza["estado"] == "SIN_EVIDENCIA_DOCUMENTAL"


def test_falla_mcp_controlada_es_error_tecnico():
    s = sistema_con([decision(accion="consultar_estado_documento", codigo_documento="DOC-1002")])
    traza = asyncio.run(s.atender("¿Está vigente DOC-1002?", cliente_supabase=None, historial=[], simular_fallo_mcp=True))
    assert traza["estado"] == "ERROR_TECNICO"


# --- Historial ---------------------------------------------------------------------
def test_historial_para_modelo_ventana():
    mensajes = []
    for n in range(6):
        mensajes += [{"rol": "usuario", "contenido": f"P{n}"}, {"rol": "asistente", "contenido": f"R{n}"}]
    turnos = historial_para_modelo(mensajes, 4)
    assert [t["usuario"] for t in turnos] == ["P2", "P3", "P4", "P5"]


def test_conversacion_ajena_o_invalida_se_rechaza():
    class Vacio:  # simula lo que devuelve Supabase cuando RLS oculta la fila
        def __getattr__(self, _):
            return lambda *a, **k: self
        data = []
    almacen = Almacenamiento("https://ejemplo.supabase.co", "sb_publishable_x")
    sesion = Sesion("11111111-1111-1111-1111-111111111111", "a@b.co", "t", "r")
    with pytest.raises(AccesoDenegado):
        almacen.comprobar_propietario(Vacio(), sesion, "no-es-un-uuid")
    with pytest.raises(AccesoDenegado):
        almacen.comprobar_propietario(Vacio(), sesion, "22222222-2222-2222-2222-222222222222")
