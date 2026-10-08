import asyncio
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from hormiguero.engine.history import History
from hormiguero.engine.mock_model import MockModel
from hormiguero.engine.parameters import apply_parameter_update, requires_rebuild
from hormiguero.engine.summary import survival_summary
from hormiguero.errors import conflict, not_found, unprocessable
from hormiguero.schemas.common import CommandAck, ErrorBody, Region
from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.events import EventCreate, EventInfo, EventStatus
from hormiguero.schemas.messages import (
    ErrorMessage,
    FieldMessage,
    FrameMessage,
    InitMessage,
    InitPayload,
    Notice,
    NoticeKind,
    NoticeMessage,
    PongMessage,
    StatusMessage,
    StatusPayload,
    Subscription,
)
from hormiguero.schemas.metrics import HistoryKey, HistoryResponse, SurvivalSummary
from hormiguero.schemas.simulation import (
    ControlAction,
    ControlRequest,
    FinishReason,
    ScenarioInfo,
    SimulationInfo,
    SimulationState,
    SimulationStatus,
)
from hormiguero.schemas.state import FieldData, FieldLayer, FrameData, NestGeometry, WorldStatic
from hormiguero.schemas.world import BrushMode, BrushStroke, FoodPlacement, PredatorPlacement, PredatorsCreated

DEFAULT_SPEED = 30.0
SUBSCRIBER_QUEUE_SIZE = 256


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:10]}"


@dataclass(eq=False)
class Subscriber:
    subscription: Subscription = field(default_factory=Subscription)
    queue: asyncio.Queue = field(default_factory=lambda: asyncio.Queue(maxsize=SUBSCRIBER_QUEUE_SIZE))

    def send(self, message: dict[str, Any]) -> None:
        with suppress(asyncio.QueueFull):
            self.queue.put_nowait(message)

    def close(self) -> None:
        while not self.queue.empty():
            self.queue.get_nowait()
        self.queue.put_nowait(None)


class Simulation:
    def __init__(self, sim_id: str, name: str, config: SimulationConfig, seed: int, scenario: ScenarioInfo | None):
        self.id = sim_id
        self.name = name
        self.config = config
        self.seed = seed
        self.scenario = scenario
        self.created_at = datetime.now(UTC)
        self.speed = DEFAULT_SPEED
        self.subscribers: set[Subscriber] = set()
        self._runner: asyncio.Task | None = None
        self._initialize()

    def _initialize(self) -> None:
        self.status = SimulationStatus.CREATED
        self.finish_reason: FinishReason | None = None
        self.collapse_tick: int | None = None
        self.events: dict[str, EventInfo] = {}
        for event in self.scenario.events if self.scenario else []:
            self._schedule(event, event.start_tick or 1)
        self._rebuild_model()

    def _rebuild_model(self) -> None:
        self.model = MockModel(self.config, self.seed)
        self.history = History()
        self.history.append(0, self.frame())

    @property
    def tick(self) -> int:
        return self.model.tick

    @property
    def sim_time(self) -> float:
        return self.model.tick * self.config.run.dt

    def info(self) -> SimulationInfo:
        return SimulationInfo(
            id=self.id,
            name=self.name,
            status=self.status,
            finish_reason=self.finish_reason,
            tick=self.tick,
            sim_time=self.sim_time,
            speed=self.speed,
            seed=self.seed,
            scenario_id=self.scenario.id if self.scenario else None,
            created_at=self.created_at,
            world_width=self.config.world.width,
            world_height=self.config.world.height,
        )

    def frame(self) -> FrameData:
        return self.model.frame([event.id for event in self.events.values() if event.status is EventStatus.ACTIVE])

    def field(self, layer: FieldLayer, downsample: int = 1) -> FieldData:
        return self.model.field(layer, downsample)

    def world_static(self) -> WorldStatic:
        world = self.config.world
        return WorldStatic(
            width=world.width,
            height=world.height,
            nest=NestGeometry(x=world.nest_x, y=world.nest_y, radius=world.nest_radius),
            obstacles=self.field(FieldLayer.OBSTACLES),
        )

    def state(self) -> SimulationState:
        return SimulationState(
            info=self.info(),
            config=self.config,
            world=self.world_static(),
            frame=self.frame(),
            events=list(self.events.values()),
        )

    def control(self, request: ControlRequest) -> SimulationInfo:
        if request.speed is not None:
            self.speed = request.speed
        match request.action:
            case ControlAction.START:
                self._start()
            case ControlAction.PAUSE:
                self._pause()
            case ControlAction.STEP:
                self._step(request.steps)
            case ControlAction.RESET:
                self._reset()
        self._broadcast(self._status_message())
        return self.info()

    def _start(self) -> None:
        if self.status in (SimulationStatus.RUNNING, SimulationStatus.FINISHED):
            raise conflict("invalid_transition", f"No se puede iniciar una simulación en estado {self.status}")
        self.status = SimulationStatus.RUNNING
        self._runner = asyncio.create_task(self._run())

    def _pause(self) -> None:
        if self.status is not SimulationStatus.RUNNING:
            raise conflict("invalid_transition", f"No se puede pausar una simulación en estado {self.status}")
        self.status = SimulationStatus.PAUSED
        self._stop_runner()

    def _step(self, steps: int) -> None:
        if self.status in (SimulationStatus.RUNNING, SimulationStatus.FINISHED):
            raise conflict("invalid_transition", f"No se puede avanzar paso a paso en estado {self.status}")
        self.status = SimulationStatus.PAUSED
        for _ in range(steps):
            self._advance()
            if self.status is SimulationStatus.FINISHED:
                break

    def _reset(self) -> None:
        self._stop_runner()
        self._initialize()
        for subscriber in self.subscribers:
            self._greet(subscriber)
        self._notify(NoticeKind.SIMULATION_RESET, "La simulación se reinició")

    async def _run(self) -> None:
        while self.status is SimulationStatus.RUNNING:
            self._advance()
            await asyncio.sleep(1 / self.speed)

    def _stop_runner(self) -> None:
        if self._runner and not self._runner.done():
            self._runner.cancel()
        self._runner = None

    def _advance(self) -> None:
        self.model.step()
        self._update_events()
        frame = self.frame()
        self.history.append(self.tick, frame)
        self._broadcast_tick(frame)
        if frame.metrics.alive_ants == 0:
            self.collapse_tick = self.tick
            self._notify(NoticeKind.COLONY_COLLAPSED, "La colonia colapsó")
            self._finish(FinishReason.COLONY_COLLAPSED)
        elif self.tick >= self.config.run.max_ticks:
            self._finish(FinishReason.MAX_TICKS)

    def _finish(self, reason: FinishReason) -> None:
        self.status = SimulationStatus.FINISHED
        self.finish_reason = reason
        self._notify(NoticeKind.SIMULATION_FINISHED, f"Simulación terminada: {reason}")
        self._broadcast(self._status_message())

    def update_parameters(self, values: dict[str, float]) -> SimulationConfig:
        is_fresh = self.status is SimulationStatus.CREATED
        self.config = apply_parameter_update(self.config, values, allow_non_live=is_fresh)
        if is_fresh and requires_rebuild(values):
            self._rebuild_model()
            for subscriber in self.subscribers:
                self._greet(subscriber)
        else:
            self.model.config = self.config
        self._notify(NoticeKind.PARAMETERS_UPDATED, "Parámetros actualizados: " + ", ".join(sorted(values)))
        return self.config

    def add_event(self, request: EventCreate) -> EventInfo:
        if self.status is SimulationStatus.FINISHED:
            raise conflict("simulation_finished", "La simulación ya terminó")
        start_tick = request.start_tick if request.start_tick is not None else self.tick + 1
        if start_tick <= self.tick:
            raise unprocessable("start_tick_in_past", "start_tick debe ser mayor al tick actual", {"tick": self.tick})
        if request.region is not None:
            self._ensure_region(request.region)
        event = self._schedule(request, start_tick)
        self._notify(NoticeKind.EVENT_SCHEDULED, f"Perturbación {event.type} programada", event_id=event.id)
        return event

    def get_event(self, event_id: str) -> EventInfo:
        if event_id not in self.events:
            raise not_found("event", event_id)
        return self.events[event_id]

    def cancel_event(self, event_id: str) -> EventInfo:
        event = self.get_event(event_id)
        if event.status in (EventStatus.FINISHED, EventStatus.CANCELLED):
            raise conflict("event_not_cancellable", f"La perturbación ya está en estado {event.status}")
        if event.status is EventStatus.ACTIVE:
            self.model.end_event(event)
        event.status = EventStatus.CANCELLED
        self._notify(NoticeKind.EVENT_CANCELLED, f"Perturbación {event.type} cancelada", event_id=event.id)
        return event

    def _schedule(self, request: EventCreate, start_tick: int) -> EventInfo:
        event = EventInfo(
            id=new_id("evt"),
            type=request.type,
            intensity=request.intensity,
            duration=request.duration,
            region=request.region,
            start_tick=start_tick,
            end_tick=start_tick + request.duration,
            predator_count=request.predator_count,
            status=EventStatus.SCHEDULED,
        )
        self.events[event.id] = event
        return event

    def _update_events(self) -> None:
        for event in self.events.values():
            if event.status is EventStatus.SCHEDULED and self.tick >= event.start_tick:
                event.status = EventStatus.ACTIVE
                self.model.start_event(event)
                self._notify(NoticeKind.EVENT_STARTED, f"Inicia la perturbación {event.type}", event_id=event.id)
            elif event.status is EventStatus.ACTIVE and self.tick >= event.end_tick:
                event.status = EventStatus.FINISHED
                self.model.end_event(event)
                self._notify(NoticeKind.EVENT_ENDED, f"Termina la perturbación {event.type}", event_id=event.id)

    def paint_obstacles(self, stroke: BrushStroke) -> CommandAck:
        for x, y in stroke.cells:
            self._ensure_cell(x, y)
        self.model.paint_obstacles(stroke.cells, stroke.radius, add=stroke.mode is BrushMode.ADD)
        self._broadcast(self._field_message(FieldLayer.OBSTACLES, 1))
        return self._acknowledge("obstacles")

    def add_food(self, placement: FoodPlacement) -> CommandAck:
        self._ensure_cell(placement.x, placement.y)
        self.model.add_food(placement.x, placement.y, placement.radius, placement.amount)
        return self._acknowledge("food")

    def add_predators(self, placement: PredatorPlacement) -> PredatorsCreated:
        self._ensure_cell(placement.x, placement.y)
        limit = self.config.predators.max_predators
        if len(self.model.predators) + placement.count > limit:
            raise conflict("predator_limit", f"Se superaría el máximo de {limit} depredadores")
        ids = self.model.add_predators(placement.x, placement.y, placement.count)
        self._acknowledge("predators_added")
        return PredatorsCreated(ids=ids, applied_at_tick=self.tick)

    def remove_predator(self, predator_id: int) -> CommandAck:
        if not self.model.remove_predator(predator_id):
            raise not_found("predator", predator_id)
        return self._acknowledge("predator_removed")

    def history_query(
        self, keys: list[HistoryKey] | None, from_tick: int, to_tick: int | None, every: int
    ) -> HistoryResponse:
        return self.history.query(keys, from_tick, to_tick, every)

    def summary(self) -> SurvivalSummary:
        return survival_summary(
            self.history,
            list(self.events.values()),
            self.collapse_tick,
            self.model.food_delivered_total,
            self.model.deaths,
        )

    def _ensure_cell(self, x: int, y: int) -> None:
        world = self.config.world
        if not (0 <= x < world.width and 0 <= y < world.height):
            raise unprocessable("out_of_bounds", f"La celda ({x}, {y}) está fuera del mundo", {"x": x, "y": y})

    def _ensure_region(self, region: Region) -> None:
        world = self.config.world
        if region.x + region.width > world.width or region.y + region.height > world.height:
            raise unprocessable("out_of_bounds", "La región sale del mundo", region.model_dump())

    def _acknowledge(self, kind: str) -> CommandAck:
        ack = CommandAck(command_id=new_id("cmd"), kind=kind, applied_at_tick=self.tick)
        self._notify(NoticeKind.COMMAND_APPLIED, f"Comando {kind} aplicado", command_id=ack.command_id)
        return ack

    def attach(self, subscriber: Subscriber) -> None:
        self.subscribers.add(subscriber)
        self._greet(subscriber)

    def detach(self, subscriber: Subscriber) -> None:
        self.subscribers.discard(subscriber)

    def update_subscription(self, subscriber: Subscriber, subscription: Subscription) -> None:
        subscriber.subscription = subscription
        for layer in subscription.layers:
            subscriber.send(self._field_message(layer, subscription.field_downsample))

    def send_pong(self, subscriber: Subscriber) -> None:
        subscriber.send(PongMessage(type="pong", tick=self.tick, sim_time=self.sim_time).model_dump(mode="json"))

    def send_error(self, subscriber: Subscriber, error: ErrorBody) -> None:
        message = ErrorMessage(type="error", tick=self.tick, sim_time=self.sim_time, payload=error)
        subscriber.send(message.model_dump(mode="json"))

    def close(self) -> None:
        self._stop_runner()
        for subscriber in self.subscribers:
            subscriber.close()
        self.subscribers.clear()

    def _greet(self, subscriber: Subscriber) -> None:
        payload = InitPayload(
            info=self.info(),
            config=self.config,
            world=self.world_static(),
            subscription=subscriber.subscription,
            events=list(self.events.values()),
        )
        subscriber.send(InitMessage(type="init", tick=self.tick, sim_time=self.sim_time, payload=payload).model_dump(mode="json"))
        subscriber.send(self._status_message())
        subscriber.send(self._frame_message(self.frame()))
        for layer in subscriber.subscription.layers:
            subscriber.send(self._field_message(layer, subscriber.subscription.field_downsample))

    def _broadcast(self, message: dict[str, Any]) -> None:
        for subscriber in self.subscribers:
            subscriber.send(message)

    def _broadcast_tick(self, frame: FrameData) -> None:
        frame_message = None
        field_messages: dict[tuple[FieldLayer, int], dict[str, Any]] = {}
        for subscriber in self.subscribers:
            subscription = subscriber.subscription
            if self.tick % subscription.frame_every == 0:
                frame_message = frame_message or self._frame_message(frame)
                subscriber.send(frame_message)
            if self.tick % subscription.field_every == 0:
                for layer in subscription.layers:
                    key = (layer, subscription.field_downsample)
                    if key not in field_messages:
                        field_messages[key] = self._field_message(*key)
                    subscriber.send(field_messages[key])

    def _notify(self, kind: NoticeKind, message: str, event_id: str | None = None, command_id: str | None = None) -> None:
        notice = Notice(kind=kind, message=message, event_id=event_id, command_id=command_id)
        self._broadcast(NoticeMessage(type="event", tick=self.tick, sim_time=self.sim_time, payload=notice).model_dump(mode="json"))

    def _status_message(self) -> dict[str, Any]:
        payload = StatusPayload(status=self.status, speed=self.speed, finish_reason=self.finish_reason)
        return StatusMessage(type="status", tick=self.tick, sim_time=self.sim_time, payload=payload).model_dump(mode="json")

    def _frame_message(self, frame: FrameData) -> dict[str, Any]:
        return FrameMessage(type="frame", tick=self.tick, sim_time=self.sim_time, payload=frame).model_dump(mode="json")

    def _field_message(self, layer: FieldLayer, downsample: int) -> dict[str, Any]:
        payload = self.field(layer, downsample)
        return FieldMessage(type="field", tick=self.tick, sim_time=self.sim_time, payload=payload).model_dump(mode="json")
