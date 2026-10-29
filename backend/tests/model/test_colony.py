import numpy as np

from hormiguero.engine.model.colony import Colony
from hormiguero.engine.model.predators import Predators
from hormiguero.engine.model.world import World
from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.state import AntRole, AntState, FieldLayer


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
