from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from hormiguero.schemas.common import ApiModel, Region


class PerturbationType(StrEnum):
    DROUGHT = "drought"
    FLOOD = "flood"
    PREDATOR_WAVE = "predator_wave"


class EventStatus(StrEnum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    FINISHED = "finished"
    CANCELLED = "cancelled"


class EventCreate(ApiModel):
    type: PerturbationType
    intensity: float = Field(0.5, ge=0, le=1)
    duration: int = Field(500, ge=1, le=100_000, description="Duración en ticks. Al terminar una oleada, sus depredadores se retiran")
    region: Region | None = Field(None, description="Área afectada. Si se omite, se afecta todo el mundo")
    start_tick: int | None = Field(None, ge=0, description="Tick de inicio. Si se omite, empieza en el siguiente tick")
    predator_count: int | None = Field(None, ge=1, le=50, description="Obligatorio para predator_wave")

    @model_validator(mode="after")
    def wave_has_predator_count(self) -> Self:
        if self.type is PerturbationType.PREDATOR_WAVE and self.predator_count is None:
            raise ValueError("predator_wave requiere predator_count")
        return self


class EventUpdate(ApiModel):
    intensity: float | None = Field(None, ge=0, le=1)
    duration: int | None = Field(None, ge=1, le=100_000)
    region: Region | None = None
    start_tick: int | None = Field(None, ge=0)
    predator_count: int | None = Field(None, ge=1, le=50)


class EventInfo(ApiModel):
    id: str
    type: PerturbationType
    intensity: float
    duration: int
    region: Region | None
    start_tick: int
    end_tick: int
    predator_count: int | None
    status: EventStatus
