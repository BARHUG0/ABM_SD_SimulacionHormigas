
import numpy as np

from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.state import FieldLayer


PHEROMONE_CAP = 100.0


class World:
    def __init__(
        self,
        config: SimulationConfig,
        rng: np.random.Generator,
        obstacles: np.ndarray | None = None,
    ) -> None:
        world = config.world

        self.rng = rng
        self.shape = (world.height, world.width)
        self.nest_x = world.nest_x
        self.nest_y = world.nest_y
        self.nest_radius = world.nest_radius

        self.layers = {
            layer: np.zeros(self.shape, dtype=np.float32)
            for layer in FieldLayer
        }

        self.layers[FieldLayer.MOISTURE].fill(1.0)

        if obstacles is not None:
            if obstacles.shape != self.shape:
                raise ValueError(
                    "Las dimensiones de los obstáculos no coinciden"
                )

            self.layers[FieldLayer.OBSTACLES][:] = (
                np.asarray(obstacles) > 0
            ).astype(np.float32)

    def sample(
        self,
        layer: FieldLayer,
        x: np.ndarray,
        y: np.ndarray,
    ) -> np.ndarray:
        x, y = np.broadcast_arrays(
            np.asarray(x),
            np.asarray(y),
        )

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

    def is_free(
        self,
        x: np.ndarray,
        y: np.ndarray,
    ) -> np.ndarray:
        x, y = np.broadcast_arrays(
            np.asarray(x),
            np.asarray(y),
        )

        inside = (
            np.isfinite(x)
            & np.isfinite(y)
            & (x >= 0)
            & (x < self.shape[1])
            & (y >= 0)
            & (y < self.shape[0])
        )

        return inside & (
            self.sample(FieldLayer.OBSTACLES, x, y) == 0
        )

    def in_nest(
        self,
        x: np.ndarray,
        y: np.ndarray,
    ) -> np.ndarray:
        x, y = np.broadcast_arrays(
            np.asarray(x),
            np.asarray(y),
        )

        distance_squared = (
            (x - self.nest_x) ** 2
            + (y - self.nest_y) ** 2
        )

        return distance_squared <= self.nest_radius ** 2

    def nest_direction(
        self,
        x: np.ndarray,
        y: np.ndarray,
    ) -> np.ndarray:
        x, y = np.broadcast_arrays(
            np.asarray(x),
            np.asarray(y),
        )

        return np.arctan2(
            self.nest_y - y,
            self.nest_x - x,
        )

    def deposit(
        self,
        layer: FieldLayer,
        x: np.ndarray,
        y: np.ndarray,
        amount: float | np.ndarray,
    ) -> None:
        pheromone_layers = (
            FieldLayer.PHEROMONE_FOOD,
            FieldLayer.PHEROMONE_HOME,
            FieldLayer.PHEROMONE_ALARM,
        )

        if layer not in pheromone_layers:
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

        xi = np.floor(x[valid] + 0.5).astype(np.int64)
        yi = np.floor(y[valid] + 0.5).astype(np.int64)

        xi = np.clip(xi, 0, self.shape[1] - 1)
        yi = np.clip(yi, 0, self.shape[0] - 1)

        free = self.layers[FieldLayer.OBSTACLES][yi, xi] == 0

        np.add.at(
            self.layers[layer],
            (yi[free], xi[free]),
            amount[valid][free],
        )

        np.clip(
            self.layers[layer],
            0,
            PHEROMONE_CAP,
            out=self.layers[layer],
        )

    def update_pheromones(
        self,
        config: SimulationConfig,
    ) -> None:
        settings = config.pheromones
        diffusion = settings.diffusion

        obstacles = self.layers[FieldLayer.OBSTACLES] > 0
        moisture = self.layers[FieldLayer.MOISTURE]
        water = self.layers[FieldLayer.WATER]

        evaporation_rates = (
            (
                FieldLayer.PHEROMONE_FOOD,
                settings.food_evaporation,
            ),
            (
                FieldLayer.PHEROMONE_HOME,
                settings.home_evaporation,
            ),
            (
                FieldLayer.PHEROMONE_ALARM,
                settings.alarm_evaporation,
            ),
        )

        for layer, evaporation in evaporation_rates:
            field = self.layers[layer]
            field[obstacles] = 0

            if diffusion > 0:
                padded = np.pad(
                    field,
                    1,
                    mode="edge",
                )

                north = padded[:-2, 1:-1]
                south = padded[2:, 1:-1]
                east = padded[1:-1, 2:]
                west = padded[1:-1, :-2]

                blocked = np.pad(
                    obstacles,
                    1,
                    mode="edge",
                )

                blocked_north = blocked[:-2, 1:-1]
                blocked_south = blocked[2:, 1:-1]
                blocked_east = blocked[1:-1, 2:]
                blocked_west = blocked[1:-1, :-2]

                neighbors = (
                    np.where(blocked_north, field, north)
                    + np.where(blocked_south, field, south)
                    + np.where(blocked_east, field, east)
                    + np.where(blocked_west, field, west)
                ) * 0.25

                field[:] = (
                    (1.0 - diffusion) * field
                    + diffusion * neighbors
                )

            effective_evaporation = np.minimum(
                1.0,
                evaporation * (
                    1.0 + 2.0 * (1.0 - moisture)
                ),
            )

            field *= 1.0 - effective_evaporation
            field *= 1.0 - 0.5 * water

            field[obstacles] = 0
            field[field < 1e-4] = 0

            np.clip(
                field,
                0,
                PHEROMONE_CAP,
                out=field,
            )
