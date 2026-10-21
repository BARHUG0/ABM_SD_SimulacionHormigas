import numpy as np

from hormiguero.engine.model.world import World
from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.common import Region
from hormiguero.schemas.events import EventInfo, EventStatus, PerturbationType
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
    result = world.is_free(np.array([-1, 10, 200]), np.array([10, 10, 10]))
    assert result.tolist() == [False, True, False]


def test_obstacles_block_cells():
    obstacles = np.zeros((200, 200), dtype=np.float32)
    obstacles[20, 30] = 1.0
    world = create_world(obstacles)
    result = world.is_free(np.array([30, 31]), np.array([20, 20]))
    assert result.tolist() == [False, True]


def test_sample_returns_zero_outside():
    world = create_world()
    world.layers[FieldLayer.FOOD][10, 20] = 5.0
    result = world.sample(
        FieldLayer.FOOD, np.array([20, -1]), np.array([10, 10])
    )
    np.testing.assert_array_equal(result, [5.0, 0.0])


def test_nest_detection():
    world = create_world()
    result = world.in_nest(
        np.array([100, 105, 120]), np.array([100, 100, 100])
    )
    assert result.tolist() == [True, True, False]


def test_nest_direction():
    world = create_world()
    result = world.nest_direction(np.array([110]), np.array([100]))
    np.testing.assert_allclose(result, [np.pi])


def test_pheromone_deposit_accumulates():
    world = create_world()
    world.deposit(
        FieldLayer.PHEROMONE_FOOD,
        np.array([20, 20, 20]),
        np.array([30, 30, 30]),
        2.0,
    )
    assert world.layers[FieldLayer.PHEROMONE_FOOD][30, 20] == 6.0


def test_pheromone_deposit_cap():
    world = create_world()
    world.deposit(
        FieldLayer.PHEROMONE_FOOD,
        np.full(1000, 20),
        np.full(1000, 30),
        1.0,
    )
    assert world.layers[FieldLayer.PHEROMONE_FOOD][30, 20] == 100.0


def test_pheromone_diffusion_conserves_mass():
    config = SimulationConfig()
    config.pheromones.diffusion = 0.2
    config.pheromones.food_evaporation = 0.0
    world = World(config, np.random.default_rng(42))
    world.deposit(FieldLayer.PHEROMONE_FOOD, np.array([50]), np.array([50]), 100.0)
    before = world.layers[FieldLayer.PHEROMONE_FOOD].sum()
    world.update_pheromones(config)
    after = world.layers[FieldLayer.PHEROMONE_FOOD].sum()
    np.testing.assert_allclose(after, before, rtol=0.001)


def test_pheromone_evaporation():
    config = SimulationConfig()
    config.pheromones.diffusion = 0.0
    config.pheromones.food_evaporation = 0.1
    world = World(config, np.random.default_rng(42))
    world.layers[FieldLayer.PHEROMONE_FOOD][50, 50] = 100.0
    for _ in range(10):
        world.update_pheromones(config)
    np.testing.assert_allclose(
        world.layers[FieldLayer.PHEROMONE_FOOD][50, 50],
        100.0 * 0.9**10,
        rtol=1e-5,
    )


def test_pheromone_water_wash():
    config = SimulationConfig()
    config.pheromones.diffusion = 0.0
    config.pheromones.food_evaporation = 0.0
    world = World(config, np.random.default_rng(42))
    world.layers[FieldLayer.PHEROMONE_FOOD][50, 50] = 100.0
    world.layers[FieldLayer.WATER][50, 50] = 1.0
    world.update_pheromones(config)
    assert world.layers[FieldLayer.PHEROMONE_FOOD][50, 50] == 50.0


def test_pheromone_drought_evaporation():
    config = SimulationConfig()
    config.pheromones.diffusion = 0.0
    config.pheromones.food_evaporation = 0.1
    world = World(config, np.random.default_rng(42))
    world.layers[FieldLayer.PHEROMONE_FOOD][50, 50] = 100.0
    world.layers[FieldLayer.MOISTURE][50, 50] = 0.0
    world.update_pheromones(config)
    assert np.isclose(world.layers[FieldLayer.PHEROMONE_FOOD][50, 50], 70.0)


def test_pheromone_cannot_cross_wall():
    config = SimulationConfig()
    config.pheromones.diffusion = 0.2
    config.pheromones.food_evaporation = 0.0
    obstacles = np.zeros((200, 200), dtype=np.float32)
    obstacles[:, 100] = 1.0
    world = World(config, np.random.default_rng(42), obstacles)
    world.deposit(FieldLayer.PHEROMONE_FOOD, np.array([99]), np.array([100]), 100.0)
    for _ in range(30):
        world.update_pheromones(config)
    assert np.all(world.layers[FieldLayer.PHEROMONE_FOOD][:, 101:] == 0.0)


def test_pheromone_mass_conserved_near_wall():
    config = SimulationConfig()
    config.pheromones.diffusion = 0.2
    config.pheromones.food_evaporation = 0.0
    obstacles = np.zeros((200, 200), dtype=np.float32)
    obstacles[:, 100] = 1.0
    world = World(config, np.random.default_rng(42), obstacles)
    world.deposit(FieldLayer.PHEROMONE_FOOD, np.array([99]), np.array([100]), 100.0)
    before = world.layers[FieldLayer.PHEROMONE_FOOD].sum()
    world.update_pheromones(config)
    after = world.layers[FieldLayer.PHEROMONE_FOOD].sum()
    np.testing.assert_allclose(after, before, rtol=0.001)


def test_pheromone_ignores_obstacle_deposits():
    obstacles = np.zeros((200, 200), dtype=np.float32)
    obstacles[30, 20] = 1.0
    world = create_world(obstacles)
    world.deposit(FieldLayer.PHEROMONE_FOOD, np.array([20]), np.array([30]), 10.0)
    assert world.layers[FieldLayer.PHEROMONE_FOOD][30, 20] == 0.0


def test_initial_food_sources_are_created():
    config = SimulationConfig()
    world = World(config, np.random.default_rng(42))
    assert len(world.food_sources) == config.world.food_sources
    assert world.food_in_world > 0


def test_food_pickup_never_exceeds_available():
    config = SimulationConfig()
    config.world.food_sources = 0
    world = World(config, np.random.default_rng(42))
    world.layers[FieldLayer.FOOD][30, 20] = 3.0
    result = world.take_food(np.full(50, 20), np.full(50, 30), 1.0)
    np.testing.assert_allclose(result.sum(), 3.0)
    assert world.layers[FieldLayer.FOOD][30, 20] == 0.0
    assert np.count_nonzero(result) == 3


def test_food_pickup_handles_multiple_cells():
    config = SimulationConfig()
    config.world.food_sources = 0
    world = World(config, np.random.default_rng(42))
    world.layers[FieldLayer.FOOD][30, 20] = 1.5
    world.layers[FieldLayer.FOOD][40, 50] = 2.0
    taken = world.take_food(
        np.array([20, 50, 20, 50]),
        np.array([30, 40, 30, 40]),
        1.0,
    )
    np.testing.assert_allclose(taken, [1.0, 1.0, 0.5, 1.0])
    assert world.food_in_world == 0.0


def test_food_regeneration_respects_capacity():
    config = SimulationConfig()
    config.world.food_sources = 0
    config.world.food_regen_rate = 5.0
    world = World(config, np.random.default_rng(42))
    world.add_food(30, 30, 2, 100.0)
    world.take_food(np.array([30]), np.array([30]), 5.0)
    for _ in range(100):
        world.update(config)
    assert world.food_in_world <= 100.001
    assert world.food_in_world > 95.0


def test_overlapping_sources_keep_combined_capacity():
    config = SimulationConfig()
    config.world.food_sources = 0
    config.world.food_regen_rate = 5.0
    world = World(config, np.random.default_rng(42))
    world.add_food(30, 30, 0, 10.0)
    world.add_food(30, 30, 0, 20.0)
    assert np.isclose(world.food_in_world, 30.0)
    world.take_food(np.array([30]), np.array([30]), 30.0)
    for _ in range(10):
        world.update(config)
    assert np.isclose(world.food_in_world, 30.0)


def test_dry_soil_reduces_regeneration():
    config = SimulationConfig()
    config.world.food_sources = 0
    config.world.food_regen_rate = 2.0
    wet = World(config, np.random.default_rng(42))
    dry = World(config, np.random.default_rng(42))
    wet.add_food(30, 30, 0, 10.0)
    dry.add_food(30, 30, 0, 10.0)
    wet.take_food(np.array([30]), np.array([30]), 5.0)
    dry.take_food(np.array([30]), np.array([30]), 5.0)
    dry.layers[FieldLayer.MOISTURE][30, 30] = 0.0
    wet.update(config)
    dry.update(config)
    assert wet.food_in_world > dry.food_in_world


def test_same_seed_produces_same_food_map():
    config = SimulationConfig()
    first = World(config, np.random.default_rng(123))
    second = World(config, np.random.default_rng(123))
    np.testing.assert_array_equal(
        first.layers[FieldLayer.FOOD], second.layers[FieldLayer.FOOD]
    )


def make_drought(event_id, intensity, region=None):
    return EventInfo(
        id=event_id,
        type=PerturbationType.DROUGHT,
        intensity=intensity,
        duration=1000,
        region=region,
        start_tick=0,
        end_tick=1000,
        predator_count=None,
        status=EventStatus.ACTIVE,
    )


def test_drought_reduces_moisture_gradually():
    config = SimulationConfig()
    world = World(config, np.random.default_rng(42))
    event = make_drought("dry-1", 0.8)
    world.start_event(event)
    assert np.all(world.layers[FieldLayer.MOISTURE] == 1.0)
    world.update(config)
    np.testing.assert_allclose(world.layers[FieldLayer.MOISTURE], 0.984, atol=1e-6)
    for _ in range(399):
        world.update(config)
    np.testing.assert_allclose(world.layers[FieldLayer.MOISTURE], 0.2, atol=0.001)


def test_drought_only_affects_its_region():
    config = SimulationConfig()
    world = World(config, np.random.default_rng(42))
    event = make_drought("dry-1", 0.5, Region(x=20, y=30, width=10, height=8))
    world.start_event(event)
    world.update(config)
    moisture = world.layers[FieldLayer.MOISTURE]
    assert np.isclose(moisture[30, 20], 0.99)
    assert np.isclose(moisture[37, 29], 0.99)
    assert moisture[29, 20] == 1.0
    assert moisture[38, 20] == 1.0
    assert moisture[30, 30] == 1.0


def test_overlapping_droughts_use_stronger_intensity():
    config = SimulationConfig()
    world = World(config, np.random.default_rng(42))
    first = make_drought("dry-1", 0.3, Region(x=10, y=10, width=20, height=20))
    second = make_drought("dry-2", 0.8, Region(x=20, y=20, width=20, height=20))
    world.start_event(first)
    world.start_event(second)
    assert np.isclose(world.moisture_target[15, 15], 0.7)
    assert np.isclose(world.moisture_target[25, 25], 0.2)
    assert np.isclose(world.moisture_target[35, 35], 0.2)
    world.end_event(second)
    assert np.isclose(world.moisture_target[25, 25], 0.7)
    assert np.isclose(world.moisture_target[35, 35], 1.0)


def test_moisture_recovers_after_drought():
    config = SimulationConfig()
    world = World(config, np.random.default_rng(42))
    event = make_drought("dry-1", 0.8)
    world.start_event(event)
    for _ in range(300):
        world.update(config)
    before = float(world.layers[FieldLayer.MOISTURE][50, 50])
    world.end_event(event)
    world.update(config)
    assert world.layers[FieldLayer.MOISTURE][50, 50] > before
    for _ in range(400):
        world.update(config)
    np.testing.assert_allclose(world.layers[FieldLayer.MOISTURE], 1.0, atol=0.001)


def test_drought_increases_pheromone_evaporation():
    config = SimulationConfig()
    config.pheromones.diffusion = 0.0
    config.pheromones.food_evaporation = 0.1
    world = World(config, np.random.default_rng(42))
    world.layers[FieldLayer.PHEROMONE_FOOD][50, 50] = 100.0
    world.start_event(make_drought("dry-1", 0.8))
    for _ in range(100):
        world.update(config)
    world.update_pheromones(config)
    actual = float(world.layers[FieldLayer.PHEROMONE_FOOD][50, 50])
    assert actual < 90.0
    assert actual > 70.0


def make_flood(event_id, intensity, region=None):
    return EventInfo(
        id=event_id,
        type=PerturbationType.FLOOD,
        intensity=intensity,
        duration=1000,
        region=region,
        start_tick=0,
        end_tick=1000,
        predator_count=None,
        status=EventStatus.ACTIVE,
    )


def test_flood_rises_gradually_and_spreads():
    config = SimulationConfig()
    world = World(config, np.random.default_rng(42))
    world.start_event(make_flood("f1", 0.8, Region(x=50, y=50, width=5, height=5)))
    assert world.layers[FieldLayer.WATER].max() == 0.0
    world.update(config)
    water = world.layers[FieldLayer.WATER]
    assert 0.0 < water[52, 52] < 0.8
    assert water[52, 49] == 0.0
    for _ in range(40):
        world.update(config)
    assert water[52, 49] > 0.0
    assert water[52, 47] == 0.0


def test_overlapping_floods_use_stronger_intensity():
    config = SimulationConfig()
    world = World(config, np.random.default_rng(42))
    first = make_flood("f1", 0.3, Region(x=10, y=10, width=20, height=20))
    second = make_flood("f2", 0.8, Region(x=20, y=20, width=20, height=20))
    world.start_event(first)
    world.start_event(second)
    assert np.isclose(world.water_target[15, 15], 0.3)
    assert np.isclose(world.water_target[25, 25], 0.8)
    assert np.isclose(world.water_target[35, 35], 0.8)
    world.end_event(second)
    assert np.isclose(world.water_target[25, 25], 0.3)
    assert np.isclose(world.water_target[35, 35], 0.0)


def test_flood_cannot_cross_wall():
    config = SimulationConfig()
    obstacles = np.zeros((200, 200), dtype=np.float32)
    obstacles[:, 100] = 1.0
    world = World(config, np.random.default_rng(42), obstacles)
    world.start_event(make_flood("f1", 1.0, Region(x=90, y=80, width=10, height=40)))
    for _ in range(120):
        world.update(config)
    water = world.layers[FieldLayer.WATER]
    assert water[:, 101:].max() == 0.0
    assert water[:, 100].max() == 0.0
    assert water[:, :100].max() > 0.0


def test_obstacle_ring_protects_nest():
    config = SimulationConfig()
    obstacles = np.zeros((200, 200), dtype=np.float32)
    obstacles[89:112, 89] = 1.0
    obstacles[89:112, 111] = 1.0
    obstacles[89, 89:112] = 1.0
    obstacles[111, 89:112] = 1.0
    world = World(config, np.random.default_rng(42), obstacles)
    world.start_event(make_flood("f1", 1.0, Region(x=75, y=75, width=14, height=50)))
    for _ in range(200):
        world.update(config)
    water = world.layers[FieldLayer.WATER]
    assert water[90:111, 90:111].max() == 0.0
    assert water[95, 88] > 0.0


def test_flood_recedes_after_event_ends():
    config = SimulationConfig()
    world = World(config, np.random.default_rng(42))
    event = make_flood("f1", 0.8, Region(x=50, y=50, width=10, height=10))
    world.start_event(event)
    for _ in range(100):
        world.update(config)
    assert world.layers[FieldLayer.WATER].max() > 0.0
    world.end_event(event)
    for _ in range(150):
        world.update(config)
    assert world.layers[FieldLayer.WATER].max() == 0.0


def test_water_stays_in_range_and_washes_pheromones():
    config = SimulationConfig()
    config.pheromones.diffusion = 0.0
    config.pheromones.food_evaporation = 0.0
    world = World(config, np.random.default_rng(42))
    world.start_event(make_flood("f1", 1.0, Region(x=50, y=50, width=10, height=10)))
    for _ in range(100):
        world.update(config)
    water = world.layers[FieldLayer.WATER]
    assert water.dtype == np.float32
    assert 0.0 <= water.min() <= water.max() <= 1.0
    world.layers[FieldLayer.PHEROMONE_FOOD][55, 55] = 100.0
    world.update_pheromones(config)
    assert world.layers[FieldLayer.PHEROMONE_FOOD][55, 55] < 100.0


def test_paint_obstacles_adds_and_erases_cells():
    world = create_world()
    assert world.paint_obstacles([(30, 30)], 0, True) == 1
    assert world.layers[FieldLayer.OBSTACLES][30, 30] == 1.0
    assert world.paint_obstacles([(30, 30)], 0, True) == 0
    assert world.paint_obstacles([(30, 30)], 0, False) == 1
    assert world.layers[FieldLayer.OBSTACLES][30, 30] == 0.0


def test_paint_obstacles_preserves_nest():
    world = create_world()
    changed = world.paint_obstacles([(world.nest_x, world.nest_y)], 0, True)
    assert changed == 0
    assert world.layers[FieldLayer.OBSTACLES][world.nest_y, world.nest_x] == 0


def test_obstacle_clears_environmental_layers():
    world = create_world()
    y, x = 40, 40
    for layer in (
        FieldLayer.FOOD,
        FieldLayer.PHEROMONE_FOOD,
        FieldLayer.PHEROMONE_HOME,
        FieldLayer.PHEROMONE_ALARM,
        FieldLayer.WATER,
    ):
        world.layers[layer][y, x] = 4.0 if layer != FieldLayer.WATER else 0.8
    world.paint_obstacles([(x, y)], 0, True)
    for layer in (
        FieldLayer.FOOD,
        FieldLayer.PHEROMONE_FOOD,
        FieldLayer.PHEROMONE_HOME,
        FieldLayer.PHEROMONE_ALARM,
        FieldLayer.WATER,
    ):
        assert world.layers[layer][y, x] == 0


def test_paint_obstacles_removes_covered_food_source():
    config = SimulationConfig()
    config.world.food_sources = 0
    world = World(config, np.random.default_rng(42))
    world.add_food(35, 35, 2, 30.0)
    assert len(world.food_sources) == 1
    world.paint_obstacles([(35, 35)], 0, True)
    assert len(world.food_sources) == 0
    for _ in range(20):
        world.update(config)
    assert world.food_in_world == 0


def test_erase_food_removes_source_and_prevents_regrowth():
    config = SimulationConfig()
    config.world.food_sources = 0
    world = World(config, np.random.default_rng(42))
    world.add_food(35, 35, 2, 30.0)
    changed = world.erase_food(35, 35, 3)
    assert changed > 0
    assert not world.food_sources
    for _ in range(20):
        world.update(config)
    assert world.food_in_world == 0


def test_erase_food_preserves_sources_outside_circle():
    config = SimulationConfig()
    config.world.food_sources = 0
    world = World(config, np.random.default_rng(42))
    world.add_food(30, 30, 1, 10.0)
    world.add_food(60, 60, 1, 10.0)
    world.erase_food(30, 30, 2)
    assert len(world.food_sources) == 1
    assert (world.food_sources[0].x, world.food_sources[0].y) == (60, 60)
    assert world.layers[FieldLayer.FOOD][60, 60] > 0


def test_reset_obstacles_can_be_reused():
    config = SimulationConfig()
    config.world.food_sources = 0
    first = World(config, np.random.default_rng(42))
    first.paint_obstacles([(35, 35)], 2, True)
    kept = first.layers[FieldLayer.OBSTACLES].copy()
    second = World(config, np.random.default_rng(42), kept)
    np.testing.assert_array_equal(second.layers[FieldLayer.OBSTACLES], kept)


def test_food_cannot_be_added_on_blocked_cell():
    config = SimulationConfig()
    config.world.food_sources = 0
    world = World(config, np.random.default_rng(42))
    world.paint_obstacles([(35, 35)], 0, True)
    assert world.add_food(35, 35, 0, 10.0) == 0
    assert world.layers[FieldLayer.FOOD][35, 35] == 0
