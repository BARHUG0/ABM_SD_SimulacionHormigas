
import numpy as np

from hormiguero.engine.model.world import World
from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.state import FieldLayer


def test_world_integration_without_hybrid():
    config = SimulationConfig()
    rng = np.random.default_rng(42)

    world = World(config, rng)

    x = np.array([30, 31, 32], dtype=np.float32)
    y = np.array([40, 40, 40], dtype=np.float32)

    world.update(config)

    assert np.all(world.is_free(x, y))

    world.add_food(30, 40, 2, 30.0)

    available = world.sample(
        FieldLayer.FOOD,
        x,
        y,
    )

    assert np.any(available > 0)

    collected = world.take_food(x, y, capacity=1.0)

    assert np.all(collected >= 0)
    assert np.all(collected <= 1.0)

    world.deposit(
        FieldLayer.PHEROMONE_FOOD,
        x,
        y,
        10.0,
    )

    world.update_pheromones(config)

    pheromones = world.layers[
        FieldLayer.PHEROMONE_FOOD
    ]

    assert np.all(np.isfinite(pheromones))
    assert np.all(pheromones >= 0)
    assert np.all(pheromones <= 100)

    assert world.food_in_world >= 0
