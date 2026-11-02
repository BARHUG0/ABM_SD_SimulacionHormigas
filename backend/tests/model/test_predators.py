import numpy as np

from hormiguero.engine.model.colony import Colony
from hormiguero.engine.model.predators import Predators
from hormiguero.engine.model.world import World
from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.state import AntState, PredatorSource, PredatorState


def setup_agents():
    config = SimulationConfig()
    config.world.food_sources = 0
    config.ants.initial_workers = 1
    config.predators.attack_probability = 1.0
    rng = np.random.default_rng(7)
    world = World(config, rng)
    colony = Colony(config, rng, world)
    predators = Predators(config, rng, world)
    return config, world, colony, predators


def test_predator_hunts_and_eats_an_ant():
    config, world, colony, predators = setup_agents()
    colony.x[0], colony.y[0] = 50, 50
    colony.state[0] = list(AntState).index(AntState.SEARCHING)
    predator_id = predators.spawn(50, 50, PredatorSource.USER)

    report = predators.step(config, world, colony)

    assert report.kills == 1
    assert predator_id in predators.items
    assert predators.items[predator_id].state is PredatorState.EATING
    assert colony.size == 0


def test_predator_dies_when_surrounded_by_soldiers():
    config, world, colony, predators = setup_agents()
    config.ants.initial_workers = 10
    colony.spawn(9, config, world)
    colony.x[:] = 50
    colony.y[:] = 50
    colony.role[:] = 2
    colony.state[:] = list(AntState).index(AntState.SEARCHING)
    predator_id = predators.spawn(50, 50, PredatorSource.USER)

    predators.step(config, world, colony)
    predators.step(config, world, colony)
    report = predators.step(config, world, colony)

    assert report.predators_died == 1
    assert predator_id not in predators.items


def test_predator_ids_are_monotonic():
    config, world, _, predators = setup_agents()
    first = predators.spawn(20, 20, PredatorSource.USER)
    predators.remove(first)
    second = predators.spawn(20, 20, PredatorSource.USER)

    assert second > first


def test_predator_catches_prey_within_one_step_of_its_speed():
    config, world, colony, predators = setup_agents()
    config.predators.speed = 2.5
    colony.x[0], colony.y[0] = 50, 50
    colony.state[0] = list(AntState).index(AntState.SEARCHING)
    predators.spawn(52, 50, PredatorSource.USER)

    report = predators.step(config, world, colony)

    assert report.kills == 1
