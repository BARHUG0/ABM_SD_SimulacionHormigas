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
        self._food_masks: list[np.ndarray] = []
        self._food_counts: list[int] = []
        self.food_capacity = np.zeros(self.shape, dtype=np.float32)
        self._place_initial_food(config)
        self._refresh_pheromone_geometry()
        self._initialize_water_buffers()

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

    def _refresh_pheromone_geometry(self) -> None:
        obstacles = self.layers[FieldLayer.OBSTACLES] > 0
        padded = np.pad(obstacles, 1, mode="edge")
        self._pheromone_obstacles = obstacles
        self._pheromone_open_neighbors = (
            ~padded[:-2, 1:-1],
            ~padded[2:, 1:-1],
            ~padded[1:-1, 2:],
            ~padded[1:-1, :-2],
        )
        open_count = np.zeros(self.shape, dtype=np.float32)
        for mask in self._pheromone_open_neighbors:
            np.add(open_count, mask, out=open_count, casting="unsafe")
        self._pheromone_blocked_count = 4.0 - open_count
        self._pheromone_neighbor_sum = np.empty(self.shape, dtype=np.float32)
        self._pheromone_scratch = np.empty(self.shape, dtype=np.float32)
        self._pheromone_dry_factor = np.empty(self.shape, dtype=np.float32)
        self._pheromone_wash_factor = np.empty(self.shape, dtype=np.float32)
        self._pheromone_center_factor = np.empty(self.shape, dtype=np.float32)

    def _initialize_water_buffers(self) -> None:
        self._water_obstacles = self.layers[FieldLayer.OBSTACLES] > 0
        self._water_free = ~self._water_obstacles
        self._water_active = np.empty(self.shape, dtype=bool)
        self._water_scratch = np.empty(self.shape, dtype=np.float32)
        self._water_neighbors = np.empty(self.shape, dtype=np.float32)
        self._water_padded = np.empty(
            (self.shape[0] + 2, self.shape[1] + 2), dtype=np.float32
        )
        self._water_open_n = np.empty(self.shape, dtype=bool)
        self._water_open_s = np.empty(self.shape, dtype=bool)
        self._water_open_e = np.empty(self.shape, dtype=bool)
        self._water_open_w = np.empty(self.shape, dtype=bool)
        self._water_blocked_count = np.empty(self.shape, dtype=np.float32)
        self._refresh_water_geometry()

    def _refresh_water_geometry(self) -> None:
        np.equal(self.layers[FieldLayer.OBSTACLES], 0, out=self._water_free)
        np.logical_not(self._water_free, out=self._water_obstacles)
        free = self._water_free
        self._water_open_n[:] = free
        self._water_open_s[:] = free
        self._water_open_e[:] = free
        self._water_open_w[:] = free
        self._water_open_n[1:, :] &= free[:-1, :]
        self._water_open_s[:-1, :] &= free[1:, :]
        self._water_open_e[:, :-1] &= free[:, 1:]
        self._water_open_w[:, 1:] &= free[:, :-1]
        self._water_open_n[0, :] = free[0, :]
        self._water_open_s[-1, :] = free[-1, :]
        self._water_open_e[:, -1] = free[:, -1]
        self._water_open_w[:, 0] = free[:, 0]
        blocked_count = self._water_blocked_count
        blocked_count.fill(4.0)
        for mask in (
            self._water_open_n,
            self._water_open_s,
            self._water_open_e,
            self._water_open_w,
        ):
            np.subtract(blocked_count, mask, out=blocked_count)

    def update_pheromones(self, config: SimulationConfig) -> None:
        settings = config.pheromones
        diffusion = float(settings.diffusion)
        obstacles = self._pheromone_obstacles
        moisture = self.layers[FieldLayer.MOISTURE]
        water = self.layers[FieldLayer.WATER]
        scratch = self._pheromone_scratch
        neighbors = self._pheromone_neighbor_sum

        np.subtract(1.0, moisture, out=self._pheromone_dry_factor)
        np.multiply(self._pheromone_dry_factor, 2.0, out=self._pheromone_dry_factor)
        np.add(self._pheromone_dry_factor, 1.0, out=self._pheromone_dry_factor)
        np.multiply(water, -0.5, out=self._pheromone_wash_factor)
        np.add(self._pheromone_wash_factor, 1.0, out=self._pheromone_wash_factor)

        if diffusion > 0:
            np.multiply(
                self._pheromone_blocked_count,
                diffusion * 0.25,
                out=self._pheromone_center_factor,
            )
            np.add(self._pheromone_center_factor, 1.0 - diffusion,
                   out=self._pheromone_center_factor)

        for layer, evaporation in (
            (FieldLayer.PHEROMONE_FOOD, settings.food_evaporation),
            (FieldLayer.PHEROMONE_HOME, settings.home_evaporation),
            (FieldLayer.PHEROMONE_ALARM, settings.alarm_evaporation),
        ):
            field = self.layers[layer]
            field[obstacles] = 0.0
            if diffusion > 0:
                neighbors.fill(0.0)
                open_n, open_s, open_e, open_w = self._pheromone_open_neighbors
                np.add(neighbors[1:, :], field[:-1, :],
                       out=neighbors[1:, :], where=open_n[1:, :])
                np.add(neighbors[:-1, :], field[1:, :],
                       out=neighbors[:-1, :], where=open_s[:-1, :])
                np.add(neighbors[:, :-1], field[:, 1:],
                       out=neighbors[:, :-1], where=open_e[:, :-1])
                np.add(neighbors[:, 1:], field[:, :-1],
                       out=neighbors[:, 1:], where=open_w[:, 1:])
                np.add(neighbors[0, :], field[0, :],
                       out=neighbors[0, :], where=open_n[0, :])
                np.add(neighbors[-1, :], field[-1, :],
                       out=neighbors[-1, :], where=open_s[-1, :])
                np.add(neighbors[:, 0], field[:, 0],
                       out=neighbors[:, 0], where=open_w[:, 0])
                np.add(neighbors[:, -1], field[:, -1],
                       out=neighbors[:, -1], where=open_e[:, -1])
                np.multiply(field, self._pheromone_center_factor, out=field)
                np.multiply(neighbors, diffusion * 0.25, out=neighbors)
                np.add(field, neighbors, out=field)

            np.multiply(self._pheromone_dry_factor, evaporation, out=scratch)
            np.minimum(scratch, 1.0, out=scratch)
            np.subtract(1.0, scratch, out=scratch)
            np.multiply(field, scratch, out=field)
            np.multiply(field, self._pheromone_wash_factor, out=field)
            field[obstacles] = 0.0
            field[field < 1e-4] = 0.0
            np.clip(field, 0.0, PHEROMONE_CAP, out=field)

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
        self._food_masks.append(mask)
        self._food_counts.append(count)
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
        self._refresh_pheromone_geometry()
        self._refresh_water_geometry()
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
        masks = []
        counts = []
        for source in self.food_sources:
            mask = disk_mask(
                self.shape, source.x, source.y, source.radius
            ) & free
            masks.append(mask)
            counts.append(int(np.count_nonzero(mask)))
            self.food_capacity[mask] += source.capacity_per_cell
        self._food_masks = masks
        self._food_counts = counts
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
        if not np.any(self.water_target) and not np.any(water):
            return

        active = self._water_active
        np.greater(self.water_target, 0.0, out=active)
        np.logical_and(active, self._water_free, out=active)
        scratch = self._water_scratch
        neighbors = self._water_neighbors

        np.subtract(self.water_target, water, out=scratch)
        np.multiply(scratch, 0.05, out=scratch)
        np.add(water, scratch, out=water, where=active)
        water[self._water_obstacles] = 0.0

        padded = self._water_padded
        padded[1:-1, 1:-1] = water
        padded[0, 1:-1] = water[0, :]
        padded[-1, 1:-1] = water[-1, :]
        padded[1:-1, 0] = water[:, 0]
        padded[1:-1, -1] = water[:, -1]

        neighbors.fill(0.0)
        np.add(neighbors, padded[:-2, 1:-1], out=neighbors,
               where=self._water_open_n)
        np.add(neighbors, padded[2:, 1:-1], out=neighbors,
               where=self._water_open_s)
        np.add(neighbors, padded[1:-1, 2:], out=neighbors,
               where=self._water_open_e)
        np.add(neighbors, padded[1:-1, :-2], out=neighbors,
               where=self._water_open_w)
        np.multiply(water, self._water_blocked_count, out=scratch)
        np.add(neighbors, scratch, out=neighbors)
        np.multiply(water, 4.0, out=scratch)
        np.subtract(scratch, neighbors, out=scratch)
        np.multiply(scratch, 0.0625, out=scratch)
        np.subtract(water, scratch, out=water)

        np.logical_not(active, out=active)
        np.subtract(water, 0.01, out=water, where=active)
        water[self._water_obstacles] = 0.0
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
        for mask, count in zip(self._food_masks, self._food_counts):
            if count == 0:
                continue
            regeneration = rate * float(moisture[mask].mean()) / count
            if regeneration > 0:
                food[mask] += regeneration
        np.minimum(food, self.food_capacity, out=food)
        food *= 1.0 - 0.001 * (1.0 - moisture)
        food[~free] = 0.0
        np.maximum(food, 0.0, out=food)
