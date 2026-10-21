
import numpy as np

from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.state import FieldLayer


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
                raise ValueError("Las dimensiones de los obstáculos no coinciden")

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
