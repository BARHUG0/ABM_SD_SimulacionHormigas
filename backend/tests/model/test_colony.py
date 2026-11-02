import numpy as np

from hormiguero.engine.model.colony import Colony
from hormiguero.engine.model.predators import Predators
from hormiguero.engine.model.world import World
from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.state import AntRole, AntState, FieldLayer, PredatorSource


def setup_colony():
    config = SimulationConfig()
    config.world.food_sources = 0
    config.ants.initial_workers = 20
    rng = np.random.default_rng(42)
    world = World(config, rng)
    colony = Colony(config, rng, world)
    predators = Predators(config, rng, world)
    return config, world, colony, predators


def test_colony_initializes_idle_agents_with_unique_ids():
    config, world, colony, _ = setup_colony()

    assert colony.size == config.ants.initial_workers
    assert np.array_equal(colony.ids, np.arange(colony.size))
    assert np.all(colony.state == list(AntState).index(AntState.IDLE_IN_NEST))
    assert np.all((colony.role >= 0) & (colony.role < len(AntRole)))


def test_colony_picks_up_and_delivers_food():
    config, world, colony, predators = setup_colony()
    config.ants.speed = 1
    config.ants.random_turn = 0
    world.add_food(130, 100, 2, 100)
    colony.x[:] = 130
    colony.y[:] = 100
    colony.state[:] = list(AntState).index(AntState.SEARCHING)
    colony.role[:] = 0
    colony.heading[:] = 0

    delivered = 0.0
    for _ in range(100):
        delivered += colony.step(config, world, predators, 1.0, 100).delivered_food
        if delivered:
            break

    assert delivered > 0
    assert np.any(world.layers[FieldLayer.PHEROMONE_FOOD] > 0)


def test_colony_death_causes_are_accumulated():
    config, world, colony, predators = setup_colony()
    config.ants.lifespan = 100
    colony.lifespan_factor[:] = 0.5
    colony.age[:] = 50

    report = colony.step(config, world, predators, 0.0, 0.0)

    assert colony.deaths.old_age == 20
    assert report.deaths.old_age == 20


def test_colony_spawn_keeps_ids_monotonic_after_removal():
    config, world, colony, _ = setup_colony()
    old_ids = colony.ids.copy()
    colony.remove(np.array([0, 1]), "starvation")
    colony.spawn(2, config, world)

    assert np.array_equal(colony.ids[-2:], old_ids[-2:] + 2)


def test_returning_ants_head_toward_the_nest_without_pheromone():
    config, world, colony, predators = setup_colony()
    config.ants.speed = 1
    config.ants.random_turn = 0
    colony.role[:] = list(AntRole).index(AntRole.FORAGER)
    colony.x[:] = 140
    colony.y[:] = 100
    colony.heading[:] = 0
    colony.state[:] = list(AntState).index(AntState.RETURNING)
    colony.load[:] = 1.0
    colony.carrying[:] = True
    start = np.hypot(colony.x - config.world.nest_x, colony.y - config.world.nest_y).mean()

    for _ in range(30):
        colony.step(config, world, predators, 1.0, 100)

    end = np.hypot(colony.x - config.world.nest_x, colony.y - config.world.nest_y).mean()
    assert end < start - 10


def test_empty_returning_ants_rest_when_they_reach_the_nest():
    config, world, colony, predators = setup_colony()
    colony.x[:] = config.world.nest_x
    colony.y[:] = config.world.nest_y
    colony.state[:] = list(AntState).index(AntState.RETURNING)
    colony.load[:] = 0.0

    colony.step(config, world, predators, 0.0, 100)

    assert np.all(colony.state == list(AntState).index(AntState.IDLE_IN_NEST))


def test_ants_keep_heading_away_while_fleeing():
    config, world, colony, predators = setup_colony()
    config.ants.speed = 1
    config.ants.random_turn = 0
    colony.role[:] = list(AntRole).index(AntRole.FORAGER)
    colony.x[:] = 50
    colony.y[:] = 50
    colony.state[:] = list(AntState).index(AntState.SEARCHING)
    colony.heading[:] = 0
    predators.spawn(52, 50, PredatorSource.USER)

    colony.step(config, world, predators, 1.0, 100)
    first = colony.x.mean()
    predators.items.clear()
    colony.step(config, world, predators, 1.0, 100)

    assert colony.x.mean() < first


def test_fleeing_ants_resume_returning_when_they_carry_food():
    config, world, colony, predators = setup_colony()
    colony.x[:] = 50
    colony.y[:] = 50
    colony.state[:] = list(AntState).index(AntState.FLEEING)
    colony.flee_timer[:] = 1
    colony.load[:] = 1.0
    colony.carrying[:] = True

    colony.step(config, world, predators, 1.0, 100)

    assert np.all(colony.state == list(AntState).index(AntState.RETURNING))


def test_ants_ignore_food_crumbs_below_the_minimum_pickup():
    config, world, colony, predators = setup_colony()
    config.ants.random_turn = 0
    config.ants.speed = 0.1
    world.add_food(130, 100, 0, 0.01)
    colony.x[:] = 130
    colony.y[:] = 100
    colony.state[:] = list(AntState).index(AntState.SEARCHING)
    colony.role[:] = list(AntRole).index(AntRole.FORAGER)

    colony.step(config, world, predators, 1.0, 100)

    assert np.all(colony.state == list(AntState).index(AntState.SEARCHING))
    assert np.all(colony.load == 0)
