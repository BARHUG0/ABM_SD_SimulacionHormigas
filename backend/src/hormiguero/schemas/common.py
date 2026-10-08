from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ErrorBody(ApiModel):
    code: str = Field(description="Código estable y legible por máquina")
    message: str
    details: Any = None


class ErrorResponse(ApiModel):
    error: ErrorBody


class HealthResponse(ApiModel):
    status: str
    version: str


class Region(ApiModel):
    x: int = Field(ge=0, description="Columna de la esquina superior izquierda")
    y: int = Field(ge=0, description="Fila de la esquina superior izquierda")
    width: int = Field(ge=1)
    height: int = Field(ge=1)


class CommandAck(ApiModel):
    command_id: str
    kind: str
    applied_at_tick: int
