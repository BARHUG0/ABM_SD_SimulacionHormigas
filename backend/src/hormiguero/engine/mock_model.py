import math
from dataclasses import dataclass

import numpy as np

from hormiguero.engine.fields import disk_mask, encode_field, stroke_mask
from hormiguero.schemas.common import Region
from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.events import EventInfo, PerturbationType
from hormiguero.schemas.state import (
    AntRole,
    AntsFrame,
    AntState,
    DeathsByCause,
    FieldData,
    FieldLayer,
    FrameData,
    FrameMetrics,
    NestFlows,
    NestFrame,
    NestStocks,
    PredatorsFrame,
    PredatorState,
)

ROLES = list(AntRole)
ANT_STATES = list(AntState)
PREDATOR_STATES = list(PredatorState)
STATE_TO_TRAIL = {
    AntState.SEARCHING: FieldLayer.PHEROMONE_HOME,
    AntState.RETURNING: FieldLayer.PHEROMONE_FOOD,
    AntState.FLEEING: FieldLayer.PHEROMONE_ALARM,
}


@dataclass
class Predator:
    x: float
    y: float
    heading: float
    state: PredatorState
    energy: float


class MockModel:
    def __init__(self, config: SimulationConfig, seed: int):
        self.config = config
        self.rng = np.random.default_rng(seed)
        self.tick = 0
        world = config.world
        self.shape = (world.height, world.width)
        self.layers = {layer: np.zeros(self.shape, dtype=np.float32) for layer in FieldLayer}
        self.layers[FieldLayer.MOISTURE].fill(1.0)
        self._place_food_sources()

        count = config.ants.initial_workers
        self.ant_ids = np.arange(count)
        self.ant_x = self._scatter(world.nest_x, world.nest_radius, count)
        self.ant_y = self._scatter(world.nest_y, world.nest_radius, count)
        self.ant_heading = self.rng.uniform(0, 2 * math.pi, count)
        self.ant_role = self.rng.integers(0, len(ROLES), count)
        self.ant_state = self.rng.integers(0, len(ANT_STATES), count)
        self.ant_energy = np.full(count, config.ants.energy_max)

        self.predators: dict[int, Predator] = {}
        self.next_predator_id = 0
        self.wave_predators: dict[str, list[int]] = {}
        for _ in range(config.predators.initial_count):
            self._spawn_predator(*self._random_cell())

        nest = config.nest
        self.stocks = NestStocks(
            food=nest.initial_food, eggs=nest.initial_eggs, larvae=nest.initial_larvae, workers=float(count)
        )
        self.flows = NestFlows(food_income=0, consumption=0, egg_laying=0, hatching=0, maturation=0, mortality=0)
        self.deaths = DeathsByCause()
        self.food_delivered_total = 0.0

    def step(self) -> None:
        self.tick += 1
        self._move_ants()
        self._move_predators()
        self._update_pheromones()
        self._update_nest()

    def frame(self, active_event_ids: list[str]) -> FrameData:
        states = [ANT_STATES[s] for s in self.ant_state]
        in_nest = sum(1 for s in states if s is AntState.IDLE_IN_NEST)
        active = len(states) - in_nest
        predators = list(self.predators.items())
        return FrameData(
            ants=AntsFrame(
                ids=self.ant_ids.tolist(),
                x=np.round(self.ant_x, 2).tolist(),
                y=np.round(self.ant_y, 2).tolist(),
                heading=np.round(self.ant_heading % (2 * math.pi), 3).tolist(),
                role=[ROLES[r] for r in self.ant_role],
                state=states,
                carrying=(self.ant_state == ANT_STATES.index(AntState.RETURNING)).tolist(),
                energy=self.ant_energy.tolist(),
            ),
            predators=PredatorsFrame(
                ids=[pid for pid, _ in predators],
                x=[round(p.x, 2) for _, p in predators],
                y=[round(p.y, 2) for _, p in predators],
                heading=[round(p.heading % (2 * math.pi), 3) for _, p in predators],
                state=[p.state for _, p in predators],
                energy=[p.energy for _, p in predators],
            ),
            nest=NestFrame(stocks=self.stocks, flows=self.flows, forager_fraction=self._forager_fraction()),
            metrics=FrameMetrics(
                alive_ants=len(states),
                foragers_active=active,
                ants_in_nest=in_nest,
                predators=len(predators),
                food_in_world=float(self.layers[FieldLayer.FOOD].sum()),
                food_delivered_total=self.food_delivered_total,
                foraging_efficiency=self.flows.food_income / active if active else 0.0,
                deaths=self.deaths,
            ),
            active_event_ids=active_event_ids,
        )

    def field(self, layer: FieldLayer, downsample: int = 1) -> FieldData:
        return encode_field(layer, self.layers[layer], downsample)

    def paint_obstacles(self, cells: list[tuple[int, int]], radius: int, add: bool) -> int:
        world = self.config.world
        mask = stroke_mask(self.shape, cells, radius)
        mask &= ~disk_mask(self.shape, world.nest_x, world.nest_y, world.nest_radius + 1)
        obstacles = self.layers[FieldLayer.OBSTACLES]
        target = 1.0 if add else 0.0
        changed = int(np.count_nonzero(obstacles[mask] != target))
        obstacles[mask] = target
        if add:
            for layer in (FieldLayer.FOOD, FieldLayer.PHEROMONE_FOOD, FieldLayer.PHEROMONE_HOME, FieldLayer.PHEROMONE_ALARM):
                self.layers[layer][mask] = 0.0
        return changed

    def add_food(self, x: int, y: int, radius: int, amount: float) -> None:
        mask = disk_mask(self.shape, x, y, radius) & (self.layers[FieldLayer.OBSTACLES] == 0)
        cells = np.count_nonzero(mask)
        if cells:
            self.layers[FieldLayer.FOOD][mask] += amount / cells

    def add_predators(self, x: int, y: int, count: int) -> list[int]:
        return [
            self._spawn_predator(
                float(np.clip(x + self.rng.normal(0, 1.5), 0, self.shape[1] - 1)),
                float(np.clip(y + self.rng.normal(0, 1.5), 0, self.shape[0] - 1)),
            )
            for _ in range(count)
        ]

    def remove_predator(self, predator_id: int) -> bool:
        return self.predators.pop(predator_id, None) is not None

    def start_event(self, event: EventInfo) -> None:
        rows, cols = self._region_slices(event.region)
        if event.type is PerturbationType.FLOOD:
            self.layers[FieldLayer.WATER][rows, cols] = event.intensity
        elif event.type is PerturbationType.DROUGHT:
            self.layers[FieldLayer.MOISTURE][rows, cols] = 1.0 - event.intensity
        elif event.type is PerturbationType.PREDATOR_WAVE:
            self.wave_predators[event.id] = [
                self._spawn_predator(*self._random_cell(event.region)) for _ in range(event.predator_count or 0)
            ]

    def end_event(self, event: EventInfo) -> None:
        rows, cols = self._region_slices(event.region)
        if event.type is PerturbationType.FLOOD:
            self.layers[FieldLayer.WATER][rows, cols] = 0.0
        elif event.type is PerturbationType.DROUGHT:
            self.layers[FieldLayer.MOISTURE][rows, cols] = 1.0
        elif event.type is PerturbationType.PREDATOR_WAVE:
            for predator_id in self.wave_predators.pop(event.id, []):
                self.remove_predator(predator_id)

    def _place_food_sources(self) -> None:
        world = self.config.world
        for _ in range(world.food_sources):
            x, y = self._random_cell()
            self.add_food(int(x), int(y), world.food_source_radius, world.food_per_source)

    def _scatter(self, center: int, radius: int, count: int) -> np.ndarray:
        return center + self.rng.uniform(-radius, radius, count)

    def _random_cell(self, region: Region | None = None) -> tuple[float, float]:
        rows, cols = self._region_slices(region)
        return float(self.rng.uniform(cols.start, cols.stop - 1)), float(self.rng.uniform(rows.start, rows.stop - 1))

    def _region_slices(self, region: Region | None) -> tuple[slice, slice]:
        if region is None:
            return slice(0, self.shape[0]), slice(0, self.shape[1])
        return slice(region.y, region.y + region.height), slice(region.x, region.x + region.width)

    def _spawn_predator(self, x: float, y: float) -> int:
        predator_id = self.next_predator_id
        self.next_predator_id += 1
        self.predators[predator_id] = Predator(
            x=x,
            y=y,
            heading=float(self.rng.uniform(0, 2 * math.pi)),
            state=PredatorState.WANDERING,
            energy=100.0,
        )
        return predator_id

    def _move_ants(self) -> None:
        ants = self.config.ants
        self.ant_heading = self.ant_heading + self.rng.normal(0, math.radians(ants.random_turn), self.ant_heading.size)
        next_x = self.ant_x + np.cos(self.ant_heading) * ants.speed
        next_y = self.ant_y + np.sin(self.ant_heading) * ants.speed
        blocked = (next_x < 0) | (next_x >= self.shape[1]) | (next_y < 0) | (next_y >= self.shape[0])
        inside = ~blocked
        blocked[inside] |= self.layers[FieldLayer.OBSTACLES][next_y[inside].astype(int), next_x[inside].astype(int)] > 0
        self.ant_x = np.where(blocked, self.ant_x, next_x)
        self.ant_y = np.where(blocked, self.ant_y, next_y)
        self.ant_heading[blocked] += math.pi
        self.ant_energy = np.maximum(self.ant_energy - ants.energy_decay, 0.0)
        if self.ant_state.size and self.tick % 50 == 0:
            self.ant_state = self.rng.integers(0, len(ANT_STATES), self.ant_state.size)

    def _move_predators(self) -> None:
        settings = self.config.predators
        for predator in self.predators.values():
            predator.heading += float(self.rng.normal(0, 0.3))
            predator.x = float(np.clip(predator.x + math.cos(predator.heading) * settings.speed, 0, self.shape[1] - 1))
            predator.y = float(np.clip(predator.y + math.sin(predator.heading) * settings.speed, 0, self.shape[0] - 1))
            predator.energy = max(predator.energy - settings.energy_decay, 0.0)
            if self.tick % 40 == 0:
                predator.state = PREDATOR_STATES[int(self.rng.integers(0, len(PREDATOR_STATES)))]

    def _update_pheromones(self) -> None:
        settings = self.config.pheromones
        cols = self.ant_x.astype(int)
        rows = self.ant_y.astype(int)
        for state, layer in STATE_TO_TRAIL.items():
            selected = self.ant_state == ANT_STATES.index(state)
            np.add.at(self.layers[layer], (rows[selected], cols[selected]), settings.deposit_amount)
        self.layers[FieldLayer.PHEROMONE_FOOD] *= 1 - settings.food_evaporation
        self.layers[FieldLayer.PHEROMONE_HOME] *= 1 - settings.home_evaporation
        self.layers[FieldLayer.PHEROMONE_ALARM] *= 1 - settings.alarm_evaporation

    def _update_nest(self) -> None:
        nest = self.config.nest
        dt = self.config.run.dt
        stocks = self.stocks
        income = float(self.rng.uniform(0, 0.02)) * stocks.workers
        consumption = stocks.workers * nest.worker_consumption + stocks.larvae * nest.larva_consumption
        egg_laying = nest.max_egg_laying_rate * stocks.food / (stocks.food + nest.food_half_saturation)
        hatching = stocks.eggs / nest.egg_duration
        maturation = stocks.larvae / nest.larva_duration
        self.flows = NestFlows(
            food_income=income,
            consumption=consumption,
            egg_laying=egg_laying,
            hatching=hatching,
            maturation=maturation,
            mortality=0.0,
        )
        self.stocks = NestStocks(
            food=max(stocks.food + (income - consumption) * dt, 0.0),
            eggs=max(stocks.eggs + (egg_laying - hatching) * dt, 0.0),
            larvae=max(stocks.larvae + (hatching - maturation) * dt, 0.0),
            workers=float(self.ant_ids.size),
        )
        self.food_delivered_total += income * dt

    def _forager_fraction(self) -> float:
        nest = self.config.nest
        workers = self.stocks.workers
        saturation = workers / (workers + nest.colony_size_half_saturation)
        return nest.min_forager_fraction + (nest.max_forager_fraction - nest.min_forager_fraction) * saturation
