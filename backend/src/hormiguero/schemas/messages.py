from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, RootModel

from hormiguero.schemas.common import ApiModel, ErrorBody
from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.events import EventInfo
from hormiguero.schemas.simulation import FinishReason, SimulationInfo, SimulationStatus
from hormiguero.schemas.state import FieldData, FieldLayer, FrameData, WorldStatic


class Subscription(ApiModel):
    layers: list[FieldLayer] = Field(
        default_factory=lambda: [FieldLayer.PHEROMONE_FOOD, FieldLayer.PHEROMONE_HOME, FieldLayer.FOOD]
    )
    frame_every: int = Field(1, ge=1, le=60, description="Enviar un frame cada N ticks")
    field_every: int = Field(10, ge=1, le=600, description="Enviar las capas suscritas cada N ticks")
    field_downsample: int = Field(2, ge=1, le=8)


class NoticeKind(StrEnum):
    EVENT_SCHEDULED = "event_scheduled"
    EVENT_STARTED = "event_started"
    EVENT_ENDED = "event_ended"
    EVENT_CANCELLED = "event_cancelled"
    COMMAND_APPLIED = "command_applied"
    PARAMETERS_UPDATED = "parameters_updated"
    COLONY_COLLAPSED = "colony_collapsed"
    SIMULATION_FINISHED = "simulation_finished"
    SIMULATION_RESET = "simulation_reset"


class Notice(ApiModel):
    kind: NoticeKind
    message: str
    event_id: str | None = None
    command_id: str | None = None


class InitPayload(ApiModel):
    info: SimulationInfo
    config: SimulationConfig
    world: WorldStatic
    subscription: Subscription
    events: list[EventInfo]


class StatusPayload(ApiModel):
    status: SimulationStatus
    speed: float
    finish_reason: FinishReason | None


class InitMessage(ApiModel):
    type: Literal["init"]
    tick: int
    sim_time: float
    payload: InitPayload


class FrameMessage(ApiModel):
    type: Literal["frame"]
    tick: int
    sim_time: float
    payload: FrameData


class FieldMessage(ApiModel):
    type: Literal["field"]
    tick: int
    sim_time: float
    payload: FieldData


class NoticeMessage(ApiModel):
    type: Literal["event"]
    tick: int
    sim_time: float
    payload: Notice


class StatusMessage(ApiModel):
    type: Literal["status"]
    tick: int
    sim_time: float
    payload: StatusPayload


class ErrorMessage(ApiModel):
    type: Literal["error"]
    tick: int
    sim_time: float
    payload: ErrorBody


class PongMessage(ApiModel):
    type: Literal["pong"]
    tick: int
    sim_time: float


class ServerMessage(RootModel):
    root: Annotated[
        InitMessage | FrameMessage | FieldMessage | NoticeMessage | StatusMessage | ErrorMessage | PongMessage,
        Field(discriminator="type"),
    ]


class SubscribeMessage(ApiModel):
    type: Literal["subscribe"]
    payload: Subscription


class PingMessage(ApiModel):
    type: Literal["ping"]


class ClientMessage(RootModel):
    root: Annotated[SubscribeMessage | PingMessage, Field(discriminator="type")]
