
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

    assert np.all(
        world.layers[FieldLayer.MOISTURE] == 1.0
    )


def test_position_outside_world_is_not_free():
    world = create_world()

    x = np.array([-1, 10, 200])
    y = np.array([10, 10, 10])

    result = world.is_free(x, y)

    assert result.tolist() == [False, True, False]


def test_obstacles_block_cells():
    obstacles = np.zeros(
        (200, 200),
        dtype=np.float32,
    )
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

    np.testing.assert_array_equal(
        result,
        [5.0, 0.0],
    )


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

    np.testing.assert_allclose(
        result,
        [np.pi],
    )


def test_pheromone_deposit_accumulates():
    world = create_world()

    world.deposit(
        FieldLayer.PHEROMONE_FOOD,
        np.array([20, 20, 20]),
        np.array([30, 30, 30]),
        2.0,
    )

    assert (
        world.layers[FieldLayer.PHEROMONE_FOOD][30, 20]
        == 6.0
    )


def test_pheromone_deposit_cap():
    world = create_world()

    world.deposit(
        FieldLayer.PHEROMONE_FOOD,
        np.full(1000, 20),
        np.full(1000, 30),
        1.0,
    )

    assert (
        world.layers[FieldLayer.PHEROMONE_FOOD][30, 20]
        == 100.0
    )


def test_pheromone_diffusion_conserves_mass():
    config = SimulationConfig()
    config.pheromones.diffusion = 0.2
    config.pheromones.food_evaporation = 0.0

    world = World(
        config,
        np.random.default_rng(42),
    )

    world.deposit(
        FieldLayer.PHEROMONE_FOOD,
        np.array([50]),
        np.array([50]),
        100.0,
    )

    before = world.layers[
        FieldLayer.PHEROMONE_FOOD
    ].sum()

    world.update_pheromones(config)

    after = world.layers[
        FieldLayer.PHEROMONE_FOOD
    ].sum()

    np.testing.assert_allclose(
        after,
        before,
        rtol=0.001,
    )


def test_pheromone_evaporation():
    config = SimulationConfig()
    config.pheromones.diffusion = 0.0
    config.pheromones.food_evaporation = 0.1

    world = World(
        config,
        np.random.default_rng(42),
    )

    world.layers[
        FieldLayer.PHEROMONE_FOOD
    ][50, 50] = 100.0

    for _ in range(10):
        world.update_pheromones(config)

    expected = 100.0 * (0.9 ** 10)

    np.testing.assert_allclose(
        world.layers[
            FieldLayer.PHEROMONE_FOOD
        ][50, 50],
        expected,
        rtol=1e-5,
    )


def test_pheromone_water_wash():
    config = SimulationConfig()
    config.pheromones.diffusion = 0.0
    config.pheromones.food_evaporation = 0.0

    world = World(
        config,
        np.random.default_rng(42),
    )

    world.layers[
        FieldLayer.PHEROMONE_FOOD
    ][50, 50] = 100.0

    world.layers[
        FieldLayer.WATER
    ][50, 50] = 1.0

    world.update_pheromones(config)

    assert (
        world.layers[FieldLayer.PHEROMONE_FOOD][50, 50]
        == 50.0
    )


def test_pheromone_drought_evaporation():
    config = SimulationConfig()
    config.pheromones.diffusion = 0.0
    config.pheromones.food_evaporation = 0.1

    world = World(
        config,
        np.random.default_rng(42),
    )

    world.layers[
        FieldLayer.PHEROMONE_FOOD
    ][50, 50] = 100.0

    world.layers[
        FieldLayer.MOISTURE
    ][50, 50] = 0.0

    world.update_pheromones(config)

    assert np.isclose(
        world.layers[
            FieldLayer.PHEROMONE_FOOD
        ][50, 50],
        70.0,
    )


def test_pheromone_cannot_cross_wall():
    config = SimulationConfig()
    config.pheromones.diffusion = 0.2
    config.pheromones.food_evaporation = 0.0

    obstacles = np.zeros(
        (200, 200),
        dtype=np.float32,
    )
    obstacles[:, 100] = 1.0

    world = World(
        config,
        np.random.default_rng(42),
        obstacles,
    )

    world.deposit(
        FieldLayer.PHEROMONE_FOOD,
        np.array([99]),
        np.array([100]),
        100.0,
    )

    for _ in range(30):
        world.update_pheromones(config)

    right_side = world.layers[
        FieldLayer.PHEROMONE_FOOD
    ][:, 101:]

    assert np.all(right_side == 0.0)


def test_pheromone_mass_conserved_near_wall():
    config = SimulationConfig()
    config.pheromones.diffusion = 0.2
    config.pheromones.food_evaporation = 0.0

    obstacles = np.zeros(
        (200, 200),
        dtype=np.float32,
    )
    obstacles[:, 100] = 1.0

    world = World(
        config,
        np.random.default_rng(42),
        obstacles,
    )

    world.deposit(
        FieldLayer.PHEROMONE_FOOD,
        np.array([99]),
        np.array([100]),
        100.0,
    )

    before = world.layers[
        FieldLayer.PHEROMONE_FOOD
    ].sum()

    world.update_pheromones(config)

    after = world.layers[
        FieldLayer.PHEROMONE_FOOD
    ].sum()

    np.testing.assert_allclose(
        after,
        before,
        rtol=0.001,
    )


def test_pheromone_ignores_obstacle_deposits():
    obstacles = np.zeros(
        (200, 200),
        dtype=np.float32,
    )
    obstacles[30, 20] = 1.0

    world = create_world(obstacles)

    world.deposit(
        FieldLayer.PHEROMONE_FOOD,
        np.array([20]),
        np.array([30]),
        10.0,
    )

    assert (
        world.layers[FieldLayer.PHEROMONE_FOOD][30, 20]
        == 0.0
    )
