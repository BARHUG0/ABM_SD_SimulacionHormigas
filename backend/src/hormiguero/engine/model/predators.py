import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.state import (
    AntRole,
    AntState,
    FieldLayer,
    PredatorSource,
    PredatorState,
    PredatorsFrame,
)

from .world import World

if TYPE_CHECKING:
    from .colony import Colony

SOLDIER_DAMAGE = 5.0
EAT_DURATION = 20


@dataclass
class Predator:
    x: float
    y: float
    heading: float
    state: PredatorState
    energy: float
    source: PredatorSource
    eat_timer: int = 0
    target_id: int | None = None


@dataclass
class PredatorReport:
    kills: int = 0
    predators_died: int = 0


class Predators:
    def __init__(
        self, config: SimulationConfig, rng: np.random.Generator, world: World
    ) -> None:
        self.rng = rng
        self.items: dict[int, Predator] = {}
        self.next_id = 0
        self.max_predators = config.predators.max_predators

    def spawn(self, x: float, y: float, source: PredatorSource) -> int:
        if len(self.items) >= self.max_predators:
            return -1
        predator_id = self.next_id
        self.next_id += 1
        self.items[predator_id] = Predator(
            x=float(x),
            y=float(y),
            heading=float(self.rng.uniform(0, 2 * math.pi)),
            state=PredatorState.WANDERING,
            energy=100.0,
            source=source,
        )
        return predator_id

    def remove(self, predator_id: int) -> bool:
        return self.items.pop(predator_id, None) is not None

    def step(
        self, config: SimulationConfig, world: World, colony: "Colony"
    ) -> PredatorReport:
        report = PredatorReport()
        if not self.items:
            return report
        active = colony.state != list(AntState).index(AntState.IDLE_IN_NEST)
        ant_ids = colony.ids[active]
        ant_x = colony.x[active]
        ant_y = colony.y[active]
        victims: list[int] = []
        dead: list[int] = []
        for predator_id, predator in list(self.items.items()):
            predator.energy -= config.predators.energy_decay
            if predator.energy <= 0:
                dead.append(predator_id)
                continue
            soldiers = (
                (colony.role[active] == list(AntRole).index(AntRole.SOLDIER))
                & (np.hypot(ant_x - predator.x, ant_y - predator.y) <= 1.5)
            )
            predator.energy -= SOLDIER_DAMAGE * int(np.count_nonzero(soldiers))
            if predator.energy <= 0:
                dead.append(predator_id)
                continue
            if predator.state is PredatorState.EATING:
                predator.eat_timer -= 1
                if predator.eat_timer <= 0:
                    predator.state = PredatorState.WANDERING
                continue
            target_index = self._target_index(predator, ant_ids, ant_x, ant_y, config.predators.vision_radius)
            if predator.state is PredatorState.HUNTING and target_index is None:
                predator.state = PredatorState.WANDERING
                predator.target_id = None
            if predator.state is PredatorState.WANDERING and target_index is not None:
                predator.state = PredatorState.HUNTING
                predator.target_id = int(ant_ids[target_index])
            if predator.state is PredatorState.HUNTING and predator.target_id is not None:
                matches = np.flatnonzero(ant_ids == predator.target_id)
                target_index = int(matches[0]) if matches.size else None
                if target_index is None:
                    predator.state = PredatorState.WANDERING
                    predator.target_id = None
                else:
                    predator.heading = math.atan2(ant_y[target_index] - predator.y, ant_x[target_index] - predator.x)
                    distance = math.hypot(ant_x[target_index] - predator.x, ant_y[target_index] - predator.y)
                    if distance <= 1.0 and predator.target_id not in victims and self.rng.random() < config.predators.attack_probability:
                        victims.append(predator.target_id)
                        report.kills += 1
                        predator.energy = min(200.0, predator.energy + config.predators.energy_gain_per_kill)
                        predator.state = PredatorState.EATING
                        predator.eat_timer = EAT_DURATION
                    else:
                        self._move(predator, config.predators.speed, world)
            else:
                predator.heading += float(self.rng.normal(0.0, 0.3))
                self._move(predator, config.predators.speed, world)
        if victims:
            indices = np.flatnonzero(np.isin(colony.ids, victims))
            colony.remove(indices, "predator")
        for predator_id in set(dead):
            if self.remove(predator_id):
                report.predators_died += 1
        return report

    def frame(self) -> PredatorsFrame:
        rows = list(self.items.items())
        return PredatorsFrame(
            ids=[pid for pid, _ in rows],
            x=[round(item.x, 1) for _, item in rows],
            y=[round(item.y, 1) for _, item in rows],
            heading=[round(item.heading % (2 * math.pi), 2) for _, item in rows],
            state=[item.state for _, item in rows],
            energy=[round(item.energy, 1) for _, item in rows],
            source=[item.source for _, item in rows],
        )

    def _target_index(
        self,
        predator: Predator,
        ids: np.ndarray,
        x: np.ndarray,
        y: np.ndarray,
        radius: float,
    ) -> int | None:
        if ids.size == 0:
            return None
        distances = np.hypot(x - predator.x, y - predator.y)
        nearest = int(np.argmin(distances))
        return nearest if distances[nearest] <= radius else None

    @staticmethod
    def _move(predator: Predator, speed: float, world: World) -> None:
        next_x = predator.x + math.cos(predator.heading) * speed
        next_y = predator.y + math.sin(predator.heading) * speed
        free = bool(world.is_free(np.array([next_x]), np.array([next_y]))[0])
        in_nest = bool(world.in_nest(np.array([next_x]), np.array([next_y]))[0])
        if free and not in_nest:
            predator.x = next_x
            predator.y = next_y
        else:
            predator.heading = (predator.heading + math.pi) % (2 * math.pi)
