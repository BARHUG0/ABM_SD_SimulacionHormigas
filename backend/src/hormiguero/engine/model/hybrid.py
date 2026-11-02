import numpy as np

from hormiguero.schemas.common import Region
from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.events import EventInfo, PerturbationType
from hormiguero.schemas.state import (
    DeathsByCause,
    FieldLayer,
    FrameData,
    FrameMetrics,
    NestFrame,
    PredatorSource,
)

from .colony import Colony
from .nest import Nest
from .predators import Predator, Predators
from .resilience import ResilienceTracker
from .world import World

SPAWN_ATTEMPTS = 50
USER_PREDATOR_SPREAD = 1.5


class HybridModel:
    def __init__(self, config: SimulationConfig, seed: int, obstacles: np.ndarray | None = None) -> None:
        self.config = config
        self.rng = np.random.default_rng(seed)
        self.tick = 0
        self.world = World(config, self.rng, obstacles)
        self.colony = Colony(config, self.rng, self.world)
        self.predators_system = Predators(config, self.rng, self.world)
        for _ in range(config.predators.initial_count):
            self.predators_system.spawn(*self._random_free_cell(), PredatorSource.INITIAL)
        self.nest = Nest(config, self.colony.size)
        self.resilience = ResilienceTracker()
        self.wave_predators: dict[str, list[int]] = {}
        self.food_delivered_total = 0.0
        self.resilience.record(0, self.colony.size, 0.0)

    @property
    def layers(self) -> dict[FieldLayer, np.ndarray]:
        return self.world.layers

    @property
    def predators(self) -> dict[int, Predator]:
        return self.predators_system.items

    @property
    def deaths(self) -> DeathsByCause:
        return self.colony.deaths

    def step(self) -> None:
        self.tick += 1
        config = self.config
        self.world.update(config)
        fraction = self.nest.forager_fraction(config, self.colony.size)
        colony_report = self.colony.step(config, self.world, self.predators_system, fraction, self.nest.stocks.food)
        predator_report = self.predators_system.step(config, self.world, self.colony)
        self.world.update_pheromones(config)
        ant_deaths = sum(colony_report.deaths.model_dump().values()) + predator_report.kills
        nest_report = self.nest.step(config, colony_report.delivered_food, self.colony.size, ant_deaths)
        self.colony.starve(nest_report.starvation_deaths)
        born = self.colony.spawn(nest_report.new_workers, config, self.world)
        self.nest.return_larvae(nest_report.new_workers - born)
        self.nest.stocks.workers = float(self.colony.size)
        self.food_delivered_total += colony_report.delivered_food
        self.resilience.record(self.tick, self.colony.size, self._foraging_efficiency())

    def frame(self, active_event_ids: list[str]) -> FrameData:
        alive = self.colony.size
        in_nest = self.colony.in_nest_count
        active = alive - in_nest
        return FrameData(
            ants=self.colony.frame(),
            predators=self.predators_system.frame(),
            nest=NestFrame(
                stocks=self.nest.stocks,
                flows=self.nest.flows,
                forager_fraction=self.nest.forager_fraction(self.config, alive),
            ),
            metrics=FrameMetrics(
                alive_ants=alive,
                foragers_active=active,
                ants_in_nest=in_nest,
                predators=len(self.predators_system.items),
                food_in_world=self.world.food_in_world,
                food_delivered_total=self.food_delivered_total,
                foraging_efficiency=self._foraging_efficiency(),
                deaths=self.colony.deaths.model_copy(),
            ),
            active_event_ids=active_event_ids,
        )

    def paint_obstacles(self, cells: list[tuple[int, int]], radius: int, add: bool) -> int:
        return self.world.paint_obstacles(cells, radius, add)

    def add_food(self, x: int, y: int, radius: int, amount: float) -> int:
        return self.world.add_food(x, y, radius, amount)

    def erase_food(self, x: int, y: int, radius: int) -> int:
        return self.world.erase_food(x, y, radius)

    def add_predators(self, x: int, y: int, count: int) -> list[int]:
        height, width = self.world.shape
        ids = []
        for _ in range(count):
            px = float(np.clip(x + self.rng.normal(0, USER_PREDATOR_SPREAD), 0, width - 1))
            py = float(np.clip(y + self.rng.normal(0, USER_PREDATOR_SPREAD), 0, height - 1))
            predator_id = self.predators_system.spawn(px, py, PredatorSource.USER)
            if predator_id >= 0:
                ids.append(predator_id)
        return ids

    def remove_predator(self, predator_id: int) -> bool:
        return self.predators_system.remove(predator_id)

    def start_event(self, event: EventInfo) -> None:
        self.resilience.start_event(event, self.colony.size)
        if event.type is PerturbationType.PREDATOR_WAVE:
            self.wave_predators[event.id] = self._spawn_wave(event)
        else:
            self.world.start_event(event)

    def end_event(self, event: EventInfo) -> None:
        if event.type is PerturbationType.PREDATOR_WAVE:
            for predator_id in self.wave_predators.pop(event.id, []):
                self.predators_system.remove(predator_id)
        else:
            self.world.end_event(event)
        self.resilience.end_event(event)

    def _spawn_wave(self, event: EventInfo) -> list[int]:
        ids = []
        for _ in range(event.predator_count or 0):
            predator_id = self.predators_system.spawn(*self._random_free_cell(event.region), PredatorSource.WAVE)
            if predator_id < 0:
                break
            ids.append(predator_id)
        return ids

    def _random_free_cell(self, region: Region | None = None) -> tuple[float, float]:
        height, width = self.world.shape
        x0, x1 = (0, width) if region is None else (region.x, region.x + region.width)
        y0, y1 = (0, height) if region is None else (region.y, region.y + region.height)
        xs = self.rng.uniform(x0, x1 - 1, SPAWN_ATTEMPTS)
        ys = self.rng.uniform(y0, y1 - 1, SPAWN_ATTEMPTS)
        free = np.flatnonzero(self.world.is_free(xs, ys))
        index = int(free[0]) if free.size else 0
        return float(xs[index]), float(ys[index])

    def _foraging_efficiency(self) -> float:
        active = self.colony.size - self.colony.in_nest_count
        return self.nest.flows.food_income / active if active else 0.0
