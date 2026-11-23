"""Servidor MCP propio del Buscador de conocimiento.

Viene del punto 4 del notebook de la Clase 11 (antes era el texto SERVIDOR_MCP que el
notebook escribía en disco). Expone una sola herramienta de lectura,
consultar_estado_documento, con los registros ficticios de la Clase 04.
La aplicación lo arranca como proceso hijo y se comunica con él por stdio.
"""
from mcp.server import MCPServer
from pydantic import BaseModel, ConfigDict, Field

mcp = MCPServer("Vigencia de documentos · Buscador de conocimiento")
DOCUMENTOS = {
    "DOC-1001": {"nombre": "Politica_Recursos_Humanos.pdf", "estado": "vigente", "detalle": "Revisado en enero de 2026; aplica a todo el personal."},
    "DOC-1002": {"nombre": "Politica_Permisos.pdf", "estado": "en_revision", "detalle": "Se está actualizando el capítulo de permisos remotos."},
    "DOC-1003": {"nombre": "Manual_Induccion.pdf", "estado": "desactualizado", "detalle": "Reemplazado por la versión 2026; pendiente de publicación."},
}


class Argumentos(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    codigo_documento: str = Field(pattern=r"^DOC-[0-9]{4}$")


class Registro(BaseModel):
    nombre: str
    estado: str
    detalle: str


class ResultadoEstado(BaseModel):
    codigo_documento: str
    encontrada: bool
    registro: Registro | None
    fuente: str


@mcp.tool()
def consultar_estado_documento(codigo_documento: str) -> ResultadoEstado:
    """Consulta la vigencia de un documento institucional ficticio por su código DOC-0000. Solo lectura."""
    codigo = Argumentos(codigo_documento=codigo_documento).codigo_documento
    registro = DOCUMENTOS.get(codigo)
    return ResultadoEstado(codigo_documento=codigo, encontrada=registro is not None,
                           registro=registro, fuente="documentos_ficticios_clase04")


if __name__ == "__main__":
    mcp.run(transport="stdio")
