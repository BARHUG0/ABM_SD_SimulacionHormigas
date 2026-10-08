from typing import Literal

from pydantic import Field

from hormiguero.schemas.common import ApiModel


class ParameterSpec(ApiModel):
    key: str = Field(description="Ruta grupo.nombre usada en PATCH /parameters")
    group: str
    name: str
    description: str
    type: Literal["int", "float"]
    default: float
    minimum: float
    maximum: float
    unit: str
    live_editable: bool = Field(description="Si es falso, solo se puede cambiar antes de iniciar o tras un reset")


class ParameterUpdate(ApiModel):
    values: dict[str, float] = Field(min_length=1, description="Mapa de clave grupo.nombre a nuevo valor")
