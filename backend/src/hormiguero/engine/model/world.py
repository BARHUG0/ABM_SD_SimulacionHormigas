from dataclasses import dataclass

import numpy as np

from hormiguero.engine.fields import disk_mask, stroke_mask
from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.events import EventInfo, PerturbationType
from hormiguero.schemas.state import FieldLayer


PHEROMONE_CAP = 100.0


@dataclass
class FoodSource:
    x: int
    y: int
    radius: int
    capacity_per_cell: float


class World:
    def __init__(
        self,
        config: SimulationConfig,
        rng: np.random.Generator,
        obstacles: np.ndarray | None = None,
    ) -> None:
        settings = config.world
        self.rng = rng
        self.shape = (settings.height, settings.width)
        self.nest_x = settings.nest_x
        self.nest_y = settings.nest_y
        self.nest_radius = settings.nest_radius
        self.layers = {
            layer: np.zeros(self.shape, dtype=np.float32)
            for layer in FieldLayer
        }
        self.layers[FieldLayer.MOISTURE].fill(1.0)

        if obstacles is not None:
            if obstacles.shape != self.shape:
                raise ValueError("Las dimensiones de los obstaculos no coinciden")
            self.layers[FieldLayer.OBSTACLES][:] = (
                np.asarray(obstacles) > 0
            ).astype(np.float32)

        self.active_events: dict[str, EventInfo] = {}
        self.moisture_target = np.ones(self.shape, dtype=np.float32)
        self.water_target = np.zeros(self.shape, dtype=np.float32)
        self.food_sources: list[FoodSource] = []
        self.food_capacity = np.zeros(self.shape, dtype=np.float32)
        self._place_initial_food(config)

    def sample(
        self, layer: FieldLayer, x: np.ndarray, y: np.ndarray
    ) -> np.ndarray:
        x, y = np.broadcast_arrays(np.asarray(x), np.asarray(y))
        valid = (
            np.isfinite(x)
            & np.isfinite(y)
            & (x >= 0)
            & (x < self.shape[1])
            & (y >= 0)
            & (y < self.shape[0])
        )
        result = np.zeros(x.shape, dtype=np.float32)
        if np.any(valid):
            xi = np.floor(x[valid] + 0.5).astype(np.int64)
            yi = np.floor(y[valid] + 0.5).astype(np.int64)
            xi = np.clip(xi, 0, self.shape[1] - 1)
            yi = np.clip(yi, 0, self.shape[0] - 1)
            result[valid] = self.layers[layer][yi, xi]
        return result

    def is_free(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        x, y = np.broadcast_arrays(np.asarray(x), np.asarray(y))
        inside = (
            np.isfinite(x)
            & np.isfinite(y)
            & (x >= 0)
            & (x < self.shape[1])
            & (y >= 0)
            & (y < self.shape[0])
        )
        return inside & (self.sample(FieldLayer.OBSTACLES, x, y) == 0)

    def in_nest(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        x, y = np.broadcast_arrays(np.asarray(x), np.asarray(y))
        return (
            (x - self.nest_x) ** 2 + (y - self.nest_y) ** 2
            <= self.nest_radius**2
        )

    def nest_direction(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        x, y = np.broadcast_arrays(np.asarray(x), np.asarray(y))
        return np.arctan2(self.nest_y - y, self.nest_x - x)

    def deposit(
        self,
        layer: FieldLayer,
        x: np.ndarray,
        y: np.ndarray,
        amount: float | np.ndarray,
    ) -> None:
        if layer not in (
            FieldLayer.PHEROMONE_FOOD,
            FieldLayer.PHEROMONE_HOME,
            FieldLayer.PHEROMONE_ALARM,
        ):
            raise ValueError("La capa no es de feromonas")
        x, y, amount = np.broadcast_arrays(
            np.asarray(x, dtype=np.float64),
            np.asarray(y, dtype=np.float64),
            np.asarray(amount, dtype=np.float32),
        )
        valid = (
            np.isfinite(x)
            & np.isfinite(y)
            & np.isfinite(amount)
            & (amount > 0)
            & (x >= 0)
            & (x < self.shape[1])
            & (y >= 0)
            & (y < self.shape[0])
        )
        if not np.any(valid):
            return
        xi = np.clip(
            np.floor(x[valid] + 0.5).astype(np.int64),
            0, self.shape[1] - 1,
        )
        yi = np.clip(
            np.floor(y[valid] + 0.5).astype(np.int64),
            0, self.shape[0] - 1,
        )
        free = self.layers[FieldLayer.OBSTACLES][yi, xi] == 0
        np.add.at(self.layers[layer], (yi[free], xi[free]), amount[valid][free])
        np.clip(self.layers[layer], 0, PHEROMONE_CAP, out=self.layers[layer])

    def update_pheromones(self, config: SimulationConfig) -> None:
        settings = config.pheromones
        diffusion = settings.diffusion
        obstacles = self.layers[FieldLayer.OBSTACLES] > 0
        moisture = self.layers[FieldLayer.MOISTURE]
        water = self.layers[FieldLayer.WATER]
        evaporation_rates = (
            (FieldLayer.PHEROMONE_FOOD, settings.food_evaporation),
            (FieldLayer.PHEROMONE_HOME, settings.home_evaporation),
            (FieldLayer.PHEROMONE_ALARM, settings.alarm_evaporation),
        )
        for layer, evaporation in evaporation_rates:
            field = self.layers[layer]
            field[obstacles] = 0
            if diffusion > 0:
                padded = np.pad(field, 1, mode="edge")
                north = padded[:-2, 1:-1]
                south = padded[2:, 1:-1]
                east = padded[1:-1, 2:]
                west = padded[1:-1, :-2]
                blocked = np.pad(obstacles, 1, mode="edge")
                neighbors = (
                    np.where(blocked[:-2, 1:-1], field, north)
                    + np.where(blocked[2:, 1:-1], field, south)
                    + np.where(blocked[1:-1, 2:], field, east)
                    + np.where(blocked[1:-1, :-2], field, west)
                ) * 0.25
                field[:] = (1.0 - diffusion) * field + diffusion * neighbors
            effective_evaporation = np.minimum(
                1.0, evaporation * (1.0 + 2.0 * (1.0 - moisture))
            )
            field *= 1.0 - effective_evaporation
            field *= 1.0 - 0.5 * water
            field[obstacles] = 0
            field[field < 1e-4] = 0
            np.clip(field, 0, PHEROMONE_CAP, out=field)

    def _place_initial_food(self, config: SimulationConfig) -> None:
        settings = config.world
        free = self.layers[FieldLayer.OBSTACLES] == 0
        outside_nest = ~disk_mask(
            self.shape, self.nest_x, self.nest_y, self.nest_radius + 1
        )
        candidates = np.flatnonzero(free & outside_nest)
        if candidates.size == 0:
            return
        for _ in range(settings.food_sources):
            index = int(self.rng.integers(candidates.size))
            row, col = np.unravel_index(candidates[index], self.shape)
            self.add_food(
                int(col), int(row),
                settings.food_source_radius, settings.food_per_source,
            )

    def add_food(self, x: int, y: int, radius: int, amount: float) -> int:
        if amount <= 0 or radius < 0:
            return 0
        mask = disk_mask(self.shape, x, y, radius)
        mask &= self.layers[FieldLayer.OBSTACLES] == 0
        count = int(np.count_nonzero(mask))
        if count == 0:
            return 0
        capacity_per_cell = float(amount) / count
        self.layers[FieldLayer.FOOD][mask] += capacity_per_cell
        self.food_capacity[mask] += capacity_per_cell
        self.food_sources.append(
            FoodSource(int(x), int(y), int(radius), capacity_per_cell)
        )
        return count

    def paint_obstacles(
        self, cells: list[tuple[int, int]], radius: int, add: bool
    ) -> int:
        if not cells or radius < 0:
            return 0
        mask = stroke_mask(self.shape, cells, radius)
        mask &= ~disk_mask(
            self.shape, self.nest_x, self.nest_y, self.nest_radius + 1
        )
        obstacles = self.layers[FieldLayer.OBSTACLES]
        target = 1.0 if add else 0.0
        changed_mask = mask & (obstacles != target)
        changed = int(np.count_nonzero(changed_mask))
        if changed == 0:
            return 0
        obstacles[changed_mask] = target
        if add:
            for layer in (
                FieldLayer.FOOD,
                FieldLayer.PHEROMONE_FOOD,
                FieldLayer.PHEROMONE_HOME,
                FieldLayer.PHEROMONE_ALARM,
                FieldLayer.WATER,
            ):
                self.layers[layer][changed_mask] = 0.0
            self.food_capacity[changed_mask] = 0.0
            self.water_target[changed_mask] = 0.0
            self.food_sources = [
                source for source in self.food_sources
                if not (
                    0 <= source.x < self.shape[1]
                    and 0 <= source.y < self.shape[0]
                    and changed_mask[source.y, source.x]
                )
            ]
            self._rebuild_food_capacity()
        else:
            self._rebuild_food_capacity()
            self._recalculate_water_target()
        return changed

    def erase_food(self, x: int, y: int, radius: int) -> int:
        if radius < 0:
            return 0
        mask = disk_mask(self.shape, x, y, radius)
        food = self.layers[FieldLayer.FOOD]
        changed = int(np.count_nonzero(mask & (food > 0)))
        food[mask] = 0.0
        self.food_sources = [
            source for source in self.food_sources
            if (source.x - x) ** 2 + (source.y - y) ** 2 > radius**2
        ]
        self._rebuild_food_capacity()
        return changed

    def _rebuild_food_capacity(self) -> None:
        self.food_capacity.fill(0.0)
        free = self.layers[FieldLayer.OBSTACLES] == 0
        for source in self.food_sources:
            mask = disk_mask(
                self.shape, source.x, source.y, source.radius
            ) & free
            self.food_capacity[mask] += source.capacity_per_cell
        np.minimum(
            self.layers[FieldLayer.FOOD],
            self.food_capacity,
            out=self.layers[FieldLayer.FOOD],
        )

    @property
    def food_in_world(self) -> float:
        return float(self.layers[FieldLayer.FOOD].sum(dtype=np.float64))

    def take_food(
        self, x: np.ndarray, y: np.ndarray, capacity: float
    ) -> np.ndarray:
        x, y = np.broadcast_arrays(
            np.asarray(x, dtype=np.float64),
            np.asarray(y, dtype=np.float64),
        )
        result = np.zeros(x.size, dtype=np.float32)
        if capacity <= 0:
            return result.reshape(x.shape)
        xf = x.ravel()
        yf = y.ravel()
        valid = (
            np.isfinite(xf)
            & np.isfinite(yf)
            & (xf >= 0)
            & (xf < self.shape[1])
            & (yf >= 0)
            & (yf < self.shape[0])
        )
        positions = np.flatnonzero(valid)
        if positions.size == 0:
            return result.reshape(x.shape)
        xi = np.clip(
            np.floor(xf[positions] + 0.5).astype(np.int64),
            0, self.shape[1] - 1,
        )
        yi = np.clip(
            np.floor(yf[positions] + 0.5).astype(np.int64),
            0, self.shape[0] - 1,
        )
        free = self.layers[FieldLayer.OBSTACLES][yi, xi] == 0
        positions = positions[free]
        xi = xi[free]
        yi = yi[free]
        if positions.size == 0:
            return result.reshape(x.shape)
        linear = yi * self.shape[1] + xi
        order = np.argsort(linear, kind="stable")
        sorted_cells = linear[order]
        sorted_positions = positions[order]
        group_start = np.r_[True, sorted_cells[1:] != sorted_cells[:-1]]
        group_indices = np.maximum.accumulate(
            np.where(group_start, np.arange(sorted_cells.size), 0)
        )
        prior_demand = (
            np.arange(sorted_cells.size) - group_indices
        ).astype(np.float64) * capacity
        food_flat = self.layers[FieldLayer.FOOD].ravel()
        available = food_flat[sorted_cells].astype(np.float64)
        picked = np.clip(available - prior_demand, 0.0, capacity)
        result[sorted_positions] = picked.astype(np.float32)
        unique_cells, first_indices = np.unique(sorted_cells, return_index=True)
        taken = np.add.reduceat(picked, first_indices)
        food_flat[unique_cells] = np.maximum(
            0.0, food_flat[unique_cells].astype(np.float64) - taken
        )
        return result.reshape(x.shape)

    def _event_mask(self, event: EventInfo) -> np.ndarray:
        if event.region is None:
            return np.ones(self.shape, dtype=bool)
        region = event.region
        mask = np.zeros(self.shape, dtype=bool)
        x0 = min(region.x, self.shape[1])
        y0 = min(region.y, self.shape[0])
        x1 = min(region.x + region.width, self.shape[1])
        y1 = min(region.y + region.height, self.shape[0])
        mask[y0:y1, x0:x1] = True
        return mask

    def _recalculate_moisture_target(self) -> None:
        self.moisture_target.fill(1.0)
        for event in self.active_events.values():
            if event.type is not PerturbationType.DROUGHT:
                continue
            mask = self._event_mask(event)
            self.moisture_target[mask] = np.minimum(
                self.moisture_target[mask], 1.0 - event.intensity
            )

    def _recalculate_water_target(self) -> None:
        self.water_target.fill(0.0)
        for event in self.active_events.values():
            if event.type is not PerturbationType.FLOOD:
                continue
            mask = self._event_mask(event)
            self.water_target[mask] = np.maximum(
                self.water_target[mask], event.intensity
            )
        self.water_target[self.layers[FieldLayer.OBSTACLES] > 0] = 0.0

    def start_event(self, event: EventInfo) -> None:
        previous = self.active_events.get(event.id)
        self.active_events[event.id] = event
        if event.type is PerturbationType.DROUGHT or (
            previous is not None and previous.type is PerturbationType.DROUGHT
        ):
            self._recalculate_moisture_target()
        if event.type is PerturbationType.FLOOD or (
            previous is not None and previous.type is PerturbationType.FLOOD
        ):
            self._recalculate_water_target()

    def end_event(self, event: EventInfo) -> None:
        removed = self.active_events.pop(event.id, None)
        if removed is not None and removed.type is PerturbationType.DROUGHT:
            self._recalculate_moisture_target()
        if removed is not None and removed.type is PerturbationType.FLOOD:
            self._recalculate_water_target()

    def _update_water(self) -> None:
        water = self.layers[FieldLayer.WATER]
        obstacles = self.layers[FieldLayer.OBSTACLES] > 0
        active = (self.water_target > 0) & ~obstacles
        water[active] += 0.05 * (self.water_target[active] - water[active])
        water[obstacles] = 0.0

        padded = np.pad(water, 1, mode="edge")
        blocked = np.pad(obstacles, 1, mode="edge")
        neighbors = (
            np.where(blocked[:-2, 1:-1], water, padded[:-2, 1:-1])
            + np.where(blocked[2:, 1:-1], water, padded[2:, 1:-1])
            + np.where(blocked[1:-1, :-2], water, padded[1:-1, :-2])
            + np.where(blocked[1:-1, 2:], water, padded[1:-1, 2:])
        ) * 0.25
        water[:] = 0.75 * water + 0.25 * neighbors
        water[~active] = np.maximum(0.0, water[~active] - 0.01)
        water[obstacles] = 0.0
        np.clip(water, 0.0, 1.0, out=water)

    def update(self, config: SimulationConfig) -> None:
        moisture = self.layers[FieldLayer.MOISTURE]
        moisture += 0.02 * (self.moisture_target - moisture)
        np.clip(moisture, 0.0, 1.0, out=moisture)
        self._update_water()
        food = self.layers[FieldLayer.FOOD]
        moisture = self.layers[FieldLayer.MOISTURE]
        free = self.layers[FieldLayer.OBSTACLES] == 0
        rate = config.world.food_regen_rate * config.run.dt
        for source in self.food_sources:
            mask = disk_mask(self.shape, source.x, source.y, source.radius)
            mask &= free
            count = int(np.count_nonzero(mask))
            if count == 0:
                continue
            regeneration = rate * float(moisture[mask].mean()) / count
            if regeneration > 0:
                food[mask] += regeneration
        np.minimum(food, self.food_capacity, out=food)
        food *= 1.0 - 0.001 * (1.0 - moisture)
        food[~free] = 0.0
        np.maximum(food, 0.0, out=food)
