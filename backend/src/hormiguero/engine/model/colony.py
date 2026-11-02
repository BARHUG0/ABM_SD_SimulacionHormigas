import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.state import (
    AntRole,
    AntState,
    AntsFrame,
    DeathsByCause,
    FieldLayer,
)

from .world import World

if TYPE_CHECKING:
    from .predators import Predators

SCOUT_FRACTION = 0.1
FLEE_DURATION = 30
HOMING_GAIN = 0.5
MIN_PICKUP_FRACTION = 0.3
FORAGING_RANGE_FRACTION = 0.35
SCOUT_RANGE_FACTOR = 1.6


@dataclass
class ColonyReport:
    delivered_food: float = 0.0
    deaths: DeathsByCause = field(default_factory=DeathsByCause)


class Colony:
    def __init__(
        self, config: SimulationConfig, rng: np.random.Generator, world: World
    ) -> None:
        self.rng = rng
        self.next_id = 0
        self.deaths = DeathsByCause()
        self.ids = np.empty(0, dtype=np.int64)
        self.x = np.empty(0, dtype=np.float64)
        self.y = np.empty(0, dtype=np.float64)
        self.heading = np.empty(0, dtype=np.float64)
        self.role = np.empty(0, dtype=np.int8)
        self.state = np.empty(0, dtype=np.int8)
        self.carrying = np.zeros(0, dtype=bool)
        self.energy = np.empty(0, dtype=np.float64)
        self.age = np.empty(0, dtype=np.int64)
        self.load = np.empty(0, dtype=np.float64)
        self.lifespan_factor = np.empty(0, dtype=np.float64)
        self.flee_timer = np.empty(0, dtype=np.int16)
        self.spawn(config.ants.initial_workers, config, world)

    @property
    def size(self) -> int:
        return int(self.ids.size)

    @property
    def in_nest_count(self) -> int:
        return int(np.count_nonzero(self.state == self._state(AntState.IDLE_IN_NEST)))

    def spawn(self, count: int, config: SimulationConfig, world: World) -> int:
        count = min(max(0, int(count)), config.ants.max_ants - self.size)
        if count == 0:
            return 0
        roles = np.full(count, self._role(AntRole.FORAGER), dtype=np.int8)
        soldier = self.rng.random(count) < config.ants.soldier_fraction
        scout = (~soldier) & (self.rng.random(count) < SCOUT_FRACTION)
        roles[soldier] = self._role(AntRole.SOLDIER)
        roles[scout] = self._role(AntRole.SCOUT)
        nest = config.world
        angles = self.rng.uniform(0, 2 * math.pi, count)
        radii = np.sqrt(self.rng.random(count)) * nest.nest_radius
        ids = np.arange(self.next_id, self.next_id + count, dtype=np.int64)
        self.next_id += count
        self.ids = np.concatenate((self.ids, ids))
        self.x = np.concatenate((self.x, nest.nest_x + np.cos(angles) * radii))
        self.y = np.concatenate((self.y, nest.nest_y + np.sin(angles) * radii))
        self.heading = np.concatenate((self.heading, self.rng.uniform(0, 2 * math.pi, count)))
        self.role = np.concatenate((self.role, roles))
        self.state = np.concatenate((self.state, np.full(count, self._state(AntState.IDLE_IN_NEST), dtype=np.int8)))
        self.carrying = np.concatenate((self.carrying, np.zeros(count, dtype=bool)))
        self.energy = np.concatenate((self.energy, np.full(count, config.ants.energy_max)))
        self.age = np.concatenate((self.age, np.zeros(count, dtype=np.int64)))
        self.load = np.concatenate((self.load, np.zeros(count, dtype=np.float64)))
        self.lifespan_factor = np.concatenate((self.lifespan_factor, self.rng.normal(1.0, 0.1, count).clip(0.5, 1.5)))
        self.flee_timer = np.concatenate((self.flee_timer, np.zeros(count, dtype=np.int16)))
        return count

    def remove(self, indices: np.ndarray, cause: str) -> int:
        indices = np.unique(np.asarray(indices, dtype=np.int64))
        indices = indices[(indices >= 0) & (indices < self.size)]
        if indices.size == 0:
            return 0
        mask = np.ones(self.size, dtype=bool)
        mask[indices] = False
        for name in (
            "ids", "x", "y", "heading", "role", "state", "carrying",
            "energy", "age", "load", "lifespan_factor", "flee_timer",
        ):
            setattr(self, name, getattr(self, name)[mask])
        setattr(self.deaths, cause, getattr(self.deaths, cause) + int(indices.size))
        return int(indices.size)

    def starve(self, count: int) -> int:
        count = min(max(0, int(count)), self.size)
        if count == 0:
            return 0
        idle = self.state == self._state(AntState.IDLE_IN_NEST)
        order = np.lexsort((self.energy, ~idle))
        return self.remove(order[:count], "starvation")

    def step(
        self,
        config: SimulationConfig,
        world: World,
        predators: "Predators",
        forager_fraction: float,
        nest_food: float,
    ) -> ColonyReport:
        report = ColonyReport()
        if self.size == 0:
            return report
        report_before = self.deaths.model_copy(deep=True)
        self.age += 1
        in_nest = world.in_nest(self.x, self.y)
        moisture = world.sample(FieldLayer.MOISTURE, self.x, self.y)
        self.energy[in_nest & (nest_food > 0)] = np.minimum(
            config.ants.energy_max, self.energy[in_nest & (nest_food > 0)] + 2
        )
        outside = ~in_nest
        self.energy[outside] -= config.ants.energy_decay * (2.0 - moisture[outside])
        low = (self.state == self._state(AntState.SEARCHING)) & (self.energy < config.ants.energy_max * 0.25)
        self.state[low] = self._state(AntState.RETURNING)
        self._release(config, forager_fraction, in_nest)
        self._flee(config, world, predators)
        self._sense_and_move(config, world, in_nest)
        searching = self.state == self._state(AntState.SEARCHING)
        pickup = searching & ~world.in_nest(self.x, self.y)
        if np.any(pickup):
            worthwhile = world.sample(FieldLayer.FOOD, self.x[pickup], self.y[pickup]) >= MIN_PICKUP_FRACTION * config.ants.carry_capacity
            pickup[pickup] = worthwhile
        if np.any(pickup):
            picked = world.take_food(self.x[pickup], self.y[pickup], config.ants.carry_capacity)
            self.load[pickup] = picked
            got = pickup.copy()
            got[pickup] = picked > 0
            self.carrying[got] = True
            self.state[got] = self._state(AntState.RETURNING)
            self.heading[got] = (self.heading[got] + math.pi) % (2 * math.pi)
        returning = self.state == self._state(AntState.RETURNING)
        deliver = returning & world.in_nest(self.x, self.y) & (self.load > 0)
        if np.any(deliver):
            report.delivered_food = float(self.load[deliver].sum())
            self.load[deliver] = 0
            self.carrying[deliver] = False
            active_target = round(forager_fraction * self.size)
            active = np.count_nonzero(self.state != self._state(AntState.IDLE_IN_NEST))
            idle_after = active >= active_target
            self.state[deliver] = np.where(idle_after, self._state(AntState.IDLE_IN_NEST), self._state(AntState.SEARCHING))
            self.heading[deliver] = (self.heading[deliver] + math.pi) % (2 * math.pi)
        arrived = (self.state == self._state(AntState.RETURNING)) & world.in_nest(self.x, self.y) & (self.load <= 0)
        self.state[arrived] = self._state(AntState.IDLE_IN_NEST)
        self._deposit(config, world)
        self._remove_deaths(config, world)
        for cause in ("predator", "flood", "starvation", "old_age"):
            setattr(report.deaths, cause, getattr(self.deaths, cause) - getattr(report_before, cause))
        return report

    def frame(self) -> AntsFrame:
        return AntsFrame(
            ids=self.ids.tolist(),
            x=np.round(self.x, 1).tolist(),
            y=np.round(self.y, 1).tolist(),
            heading=np.round(self.heading % (2 * math.pi), 2).tolist(),
            role=self.role.tolist(),
            state=self.state.tolist(),
            carrying=self.carrying.tolist(),
            energy=np.round(self.energy, 1).tolist(),
            age=self.age.tolist(),
        )

    def _release(self, config: SimulationConfig, fraction: float, in_nest: np.ndarray) -> None:
        target = round(fraction * self.size)
        active = np.count_nonzero(self.state != self._state(AntState.IDLE_IN_NEST))
        count = min(max(0, target - active), max(1, math.ceil(self.size * 0.05)))
        eligible = np.flatnonzero(
            (self.state == self._state(AntState.IDLE_IN_NEST))
            & (self.energy > config.ants.energy_max * 0.5)
        )
        if count and eligible.size:
            chosen = self.rng.choice(eligible, min(count, eligible.size), replace=False)
            self.state[chosen] = self._state(AntState.SEARCHING)
            self.heading[chosen] = self.rng.uniform(0, 2 * math.pi, chosen.size)

    def _flee(self, config: SimulationConfig, world: World, predators: "Predators") -> None:
        if predators.items:
            self._detect_predators(config, world, predators)
        fleeing = self.state == self._state(AntState.FLEEING)
        self.flee_timer[fleeing] -= 1
        done = fleeing & (self.flee_timer <= 0)
        self.state[done] = np.where(
            self.load[done] > 0, self._state(AntState.RETURNING), self._state(AntState.SEARCHING)
        )

    def _detect_predators(self, config: SimulationConfig, world: World, predators: "Predators") -> None:
        predator_positions = np.array([(p.x, p.y) for p in predators.items.values()])
        distances = ((self.x[:, None] - predator_positions[:, 0]) ** 2 + (self.y[:, None] - predator_positions[:, 1]) ** 2)
        nearest = np.argmin(distances, axis=1)
        visible = distances[np.arange(self.size), nearest] <= (config.predators.vision_radius / 2) ** 2
        eligible = visible & (self.role != self._role(AntRole.SOLDIER)) & (self.state != self._state(AntState.IDLE_IN_NEST))
        self.state[eligible] = self._state(AntState.FLEEING)
        self.flee_timer[eligible] = FLEE_DURATION
        if np.any(eligible):
            target = predator_positions[nearest[eligible]]
            self.heading[eligible] = np.arctan2(self.y[eligible] - target[:, 1], self.x[eligible] - target[:, 0])
            world.deposit(FieldLayer.PHEROMONE_ALARM, self.x[eligible], self.y[eligible], config.pheromones.deposit_amount)

    def _sense_and_move(self, config: SimulationConfig, world: World, in_nest: np.ndarray) -> None:
        movable = self.state != self._state(AntState.IDLE_IN_NEST)
        if not np.any(movable):
            return
        angle = math.radians(config.ants.sensor_angle)
        distance = config.ants.sensor_distance
        selected = np.flatnonzero(movable)
        left = self.heading[selected] - angle
        right = self.heading[selected] + angle
        sensor_x = np.stack((self.x[selected] + np.cos(left) * distance, self.x[selected] + np.cos(self.heading[selected]) * distance, self.x[selected] + np.cos(right) * distance))
        sensor_y = np.stack((
            self.y[selected] + np.sin(left) * distance,
            self.y[selected] + np.sin(self.heading[selected]) * distance,
            self.y[selected] + np.sin(right) * distance,
        ))
        food = world.sample(FieldLayer.PHEROMONE_FOOD, sensor_x, sensor_y)
        home = world.sample(FieldLayer.PHEROMONE_HOME, sensor_x, sensor_y)
        alarm = world.sample(FieldLayer.PHEROMONE_ALARM, sensor_x, sensor_y)
        scores = np.where(self.state[selected] == self._state(AntState.RETURNING), home, food - alarm)
        best = np.argmax(scores, axis=0)
        use_sensor = scores[best, np.arange(best.size)] > 0.05
        turns = np.zeros(best.size)
        scout = self.role[selected] == self._role(AntRole.SCOUT)
        turns[best == 0] = -angle
        turns[best == 2] = angle
        turns[~use_sensor] = 0
        ignore = scout & (self.rng.random(best.size) < 0.8)
        turns[ignore] = 0
        distance_to_nest = np.hypot(self.x[selected] - world.nest_x, self.y[selected] - world.nest_y)
        range_limit = FORAGING_RANGE_FRACTION * min(world.shape) * np.where(scout, SCOUT_RANGE_FACTOR, 1.0)
        straying = (self.state[selected] == self._state(AntState.SEARCHING)) & ~use_sensor & (distance_to_nest > range_limit)
        homing = (self.state[selected] == self._state(AntState.RETURNING)) | straying
        if np.any(homing):
            toward = world.nest_direction(self.x[selected[homing]], self.y[selected[homing]])
            offset = (toward - self.heading[selected[homing]] + math.pi) % (2 * math.pi) - math.pi
            turns[homing] = HOMING_GAIN * offset
        turn_limit = math.radians(config.ants.random_turn) * np.where(scout, 2.0, 1.0)
        self.heading[selected] += turns + self.rng.uniform(-turn_limit, turn_limit)
        next_x = self.x[selected] + np.cos(self.heading[selected]) * config.ants.speed
        next_y = self.y[selected] + np.sin(self.heading[selected]) * config.ants.speed
        free = world.is_free(next_x, next_y)
        blocked = ~free
        if np.any(blocked):
            turn = np.where(self.rng.random(np.count_nonzero(blocked)) < 0.5, math.pi / 2, -math.pi / 2)
            blocked_indices = selected[blocked]
            alternate = self.heading[blocked_indices] + turn
            alt_x = self.x[blocked_indices] + np.cos(alternate) * config.ants.speed
            alt_y = self.y[blocked_indices] + np.sin(alternate) * config.ants.speed
            alternate_free = world.is_free(alt_x, alt_y)
            next_x[blocked] = np.where(alternate_free, alt_x, self.x[blocked_indices])
            next_y[blocked] = np.where(alternate_free, alt_y, self.y[blocked_indices])
            self.heading[blocked_indices] = np.where(alternate_free, alternate, self.heading[blocked_indices] + math.pi)
        self.x[selected] = next_x
        self.y[selected] = next_y

    def _deposit(self, config: SimulationConfig, world: World) -> None:
        for state, layer in (
            (AntState.SEARCHING, FieldLayer.PHEROMONE_HOME),
            (AntState.RETURNING, FieldLayer.PHEROMONE_FOOD),
            (AntState.FLEEING, FieldLayer.PHEROMONE_ALARM),
        ):
            mask = self.state == self._state(state)
            if np.any(mask):
                world.deposit(layer, self.x[mask], self.y[mask], config.pheromones.deposit_amount)

    def _remove_deaths(self, config: SimulationConfig, world: World) -> None:
        causes = np.zeros(self.size, dtype=object)
        causes[self.age >= config.ants.lifespan * self.lifespan_factor] = "old_age"
        causes[(self.energy <= 0) & (causes == 0)] = "starvation"
        water = world.sample(FieldLayer.WATER, self.x, self.y)
        drowned = (water > 0.3) & (self.rng.random(self.size) < 0.05 * water)
        causes[drowned & (causes == 0)] = "flood"
        indices = np.flatnonzero(causes != 0)
        if indices.size == 0:
            return
        mask = np.ones(self.size, dtype=bool)
        mask[indices] = False
        for name in (
            "ids", "x", "y", "heading", "role", "state", "carrying",
            "energy", "age", "load", "lifespan_factor", "flee_timer",
        ):
            setattr(self, name, getattr(self, name)[mask])
        for cause in ("old_age", "starvation", "flood"):
            setattr(self.deaths, cause, getattr(self.deaths, cause) + int(np.count_nonzero(causes == cause)))

    @staticmethod
    def _role(role: AntRole) -> int:
        return list(AntRole).index(role)

    @staticmethod
    def _state(state: AntState) -> int:
        return list(AntState).index(state)
