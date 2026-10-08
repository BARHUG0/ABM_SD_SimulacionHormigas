from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from hormiguero.schemas.common import ApiModel
from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.events import EventCreate, EventInfo
from hormiguero.schemas.state import FrameData, WorldStatic


class SimulationStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    FINISHED = "finished"


class FinishReason(StrEnum):
    MAX_TICKS = "max_ticks"
    COLONY_COLLAPSED = "colony_collapsed"


class ControlAction(StrEnum):
    START = "start"
    PAUSE = "pause"
    STEP = "step"
    RESET = "reset"
    SET_SPEED = "set_speed"


class ScenarioInfo(ApiModel):
    id: str
    name: str
    description: str
    config: SimulationConfig
    events: list[EventCreate]


class SimulationCreate(ApiModel):
    name: str | None = Field(None, max_length=80)
    scenario_id: str | None = None
    config: SimulationConfig | None = None
    seed: int | None = Field(None, ge=0, le=2**32 - 1)

    @model_validator(mode="after")
    def scenario_or_config(self) -> Self:
        if self.scenario_id is not None and self.config is not None:
            raise ValueError("Use scenario_id o config, no ambos")
        return self


class ControlRequest(ApiModel):
    action: ControlAction
    steps: int = Field(1, ge=1, le=1000, description="Solo aplica a step")
    speed: float | None = Field(None, ge=1, le=120, description="Ticks por segundo. Obligatorio para set_speed")
    seed: int | None = Field(None, ge=0, le=2**32 - 1, description="Solo aplica a reset. Nueva semilla")
    keep_obstacles: bool = Field(False, description="Solo aplica a reset. Conserva los obstáculos dibujados")

    @model_validator(mode="after")
    def options_match_action(self) -> Self:
        if self.action is ControlAction.SET_SPEED and self.speed is None:
            raise ValueError("set_speed requiere speed")
        if self.action is not ControlAction.RESET and (self.seed is not None or self.keep_obstacles):
            raise ValueError("seed y keep_obstacles solo aplican a reset")
        return self


class SimulationInfo(ApiModel):
    id: str
    name: str
    status: SimulationStatus
    finish_reason: FinishReason | None
    tick: int
    sim_time: float
    speed: float
    seed: int
    scenario_id: str | None
    created_at: datetime
    world_width: int
    world_height: int


class SimulationState(ApiModel):
    info: SimulationInfo
    config: SimulationConfig
    world: WorldStatic
    frame: FrameData
    events: list[EventInfo]
