from enum import StrEnum

from pydantic import Field

from hormiguero.schemas.common import ApiModel


class BrushMode(StrEnum):
    ADD = "add"
    ERASE = "erase"


class BrushStroke(ApiModel):
    cells: list[tuple[int, int]] = Field(min_length=1, max_length=5000, description="Celdas [x, y] recorridas por el pincel")
    radius: int = Field(1, ge=0, le=10)
    mode: BrushMode = BrushMode.ADD


class FoodPlacement(ApiModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    radius: int = Field(3, ge=1, le=20)
    amount: float = Field(100.0, gt=0, le=10_000, description="Se ignora en modo erase")
    mode: BrushMode = BrushMode.ADD


class PredatorPlacement(ApiModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    count: int = Field(1, ge=1, le=20)


class PredatorsCreated(ApiModel):
    ids: list[int]
    x: list[float]
    y: list[float]
    applied_at_tick: int
