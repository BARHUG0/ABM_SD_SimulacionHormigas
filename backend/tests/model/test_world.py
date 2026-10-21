
import numpy as np

from hormiguero.engine.model.world import World
from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.state import FieldLayer


def create_world(obstacles=None):
    config = SimulationConfig()
    rng = np.random.default_rng(42)
    return World(config, rng, obstacles)


def test_world_has_seven_layers():
    world = create_world()

    assert len(world.layers) == 7

    for layer in FieldLayer:
        assert world.layers[layer].shape == (200, 200)
        assert world.layers[layer].dtype == np.float32


def test_initial_moisture():
    world = create_world()

    assert np.all(world.layers[FieldLayer.MOISTURE] == 1.0)


def test_position_outside_world_is_not_free():
    world = create_world()

    x = np.array([-1, 10, 200])
    y = np.array([10, 10, 10])

    result = world.is_free(x, y)

    assert result.tolist() == [False, True, False]


def test_obstacles_block_cells():
    obstacles = np.zeros((200, 200), dtype=np.float32)
    obstacles[20, 30] = 1.0

    world = create_world(obstacles)

    result = world.is_free(
        np.array([30, 31]),
        np.array([20, 20]),
    )

    assert result.tolist() == [False, True]


def test_sample_returns_zero_outside():
    world = create_world()
    world.layers[FieldLayer.FOOD][10, 20] = 5.0

    result = world.sample(
        FieldLayer.FOOD,
        np.array([20, -1]),
        np.array([10, 10]),
    )

    np.testing.assert_array_equal(result, [5.0, 0.0])


def test_nest_detection():
    world = create_world()

    result = world.in_nest(
        np.array([100, 105, 120]),
        np.array([100, 100, 100]),
    )

    assert result.tolist() == [True, True, False]


def test_nest_direction():
    world = create_world()

    result = world.nest_direction(
        np.array([110]),
        np.array([100]),
    )

    np.testing.assert_allclose(result, [np.pi])
