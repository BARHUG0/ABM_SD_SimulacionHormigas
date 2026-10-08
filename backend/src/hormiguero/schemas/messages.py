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
    EVENT_UPDATED = "event_updated"
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
    event: EventInfo | None = None
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


class Envelope(ApiModel):
    seq: int = Field(description="Consecutivo por conexión. Un salto indica mensajes perdidos: pedir GET /state")
    tick: int
    sim_time: float


class InitMessage(Envelope):
    type: Literal["init"]
    payload: InitPayload


class FrameMessage(Envelope):
    type: Literal["frame"]
    payload: FrameData


class FieldMessage(Envelope):
    type: Literal["field"]
    payload: FieldData


class NoticeMessage(Envelope):
    type: Literal["event"]
    payload: Notice


class StatusMessage(Envelope):
    type: Literal["status"]
    payload: StatusPayload


class ConfigMessage(Envelope):
    type: Literal["config"]
    payload: SimulationConfig


class ErrorMessage(Envelope):
    type: Literal["error"]
    payload: ErrorBody


class PongMessage(Envelope):
    type: Literal["pong"]


class ServerMessage(RootModel):
    root: Annotated[
        InitMessage
        | FrameMessage
        | FieldMessage
        | NoticeMessage
        | StatusMessage
        | ConfigMessage
        | ErrorMessage
        | PongMessage,
        Field(discriminator="type"),
    ]


class SubscribeMessage(ApiModel):
    type: Literal["subscribe"]
    payload: Subscription


class PingMessage(ApiModel):
    type: Literal["ping"]


class ClientMessage(RootModel):
    root: Annotated[SubscribeMessage | PingMessage, Field(discriminator="type")]
