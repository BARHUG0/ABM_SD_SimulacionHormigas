import math

from hormiguero.engine.model.nest import Nest
from hormiguero.schemas.config import AntConfig, NestConfig, SimulationConfig


def euler_reference(config, workers, ticks):
    nest = config.nest
    food, eggs, larvae = nest.initial_food, nest.initial_eggs, nest.initial_larvae
    carry = 0.0
    history = []
    for _ in range(ticks):
        demand = workers * nest.worker_consumption + larvae * nest.larva_consumption
        consumption = min(demand, food)
        hunger = (demand - consumption) / demand if demand else 0.0
        laying = nest.max_egg_laying_rate * food / (food + nest.food_half_saturation)
        hatching = eggs / nest.egg_duration
        carry += larvae / nest.larva_duration
        born = math.floor(carry)
        carry -= born
        history.append((food, eggs, larvae))
        food = max(food - consumption, 0.0)
        eggs = max(eggs + laying - hatching, 0.0)
        larvae = max(larvae + hatching - nest.starvation_mortality * hunger * larvae - born, 0.0)
    return history


def test_stocks_follow_hand_computed_euler_solution():
    config = SimulationConfig()
    nest = Nest(config, workers=100)
    reference = euler_reference(config, 100, 10)
    for food, eggs, larvae in reference:
        assert math.isclose(nest.stocks.food, food, rel_tol=1e-9)
        assert math.isclose(nest.stocks.eggs, eggs, rel_tol=1e-9)
        assert math.isclose(nest.stocks.larvae, larvae, rel_tol=1e-9)
        nest.step(config, delivered_food=0.0, workers=100, ant_deaths=0)


def test_income_converts_with_dt():
    config = SimulationConfig(run={"dt": 0.5})
    nest = Nest(config, workers=10)
    nest.step(config, delivered_food=2.0, workers=10, ant_deaths=0)
    assert nest.flows.food_income == 4.0


def test_without_food_hunger_is_full_and_starvation_matches_mortality():
    config = SimulationConfig(nest=NestConfig(initial_food=0.0))
    nest = Nest(config, workers=100)
    deaths = 0
    ticks = 200
    for _ in range(ticks):
        report = nest.step(config, delivered_food=0.0, workers=100, ant_deaths=0)
        deaths += report.starvation_deaths
        assert nest.flows.consumption == 0.0
        assert nest.hunger == 1.0
    assert abs(deaths - config.nest.starvation_mortality * 100 * ticks) <= 1


def test_matured_larvae_match_integrated_maturation():
    config = SimulationConfig(ants=AntConfig(max_ants=5000), nest=NestConfig(initial_food=10000.0))
    nest = Nest(config, workers=10)
    expected = 0.0
    born = 0
    for _ in range(1000):
        expected += nest.stocks.larvae / config.nest.larva_duration
        born += nest.step(config, delivered_food=0.0, workers=10, ant_deaths=0).new_workers
    assert abs(born - expected) <= 1


def test_full_colony_keeps_larvae_waiting():
    config = SimulationConfig(ants=AntConfig(max_ants=100), nest=NestConfig(initial_food=10000.0))
    nest = Nest(config, workers=100)
    previous = nest.stocks.larvae
    for _ in range(500):
        report = nest.step(config, delivered_food=0.0, workers=100, ant_deaths=0)
        assert report.new_workers == 0
        assert nest.stocks.larvae >= previous
        previous = nest.stocks.larvae


def test_return_larvae_restores_stock():
    config = SimulationConfig()
    nest = Nest(config, workers=10)
    before = nest.stocks.larvae
    nest.return_larvae(3)
    assert nest.stocks.larvae == before + 3
    nest.return_larvae(0)
    assert nest.stocks.larvae == before + 3


def test_mortality_flow_counts_ant_deaths_and_starvation():
    config = SimulationConfig(nest=NestConfig(initial_food=0.0, starvation_mortality=1.0))
    nest = Nest(config, workers=10)
    report = nest.step(config, delivered_food=0.0, workers=10, ant_deaths=4)
    assert nest.flows.mortality == 4 + report.starvation_deaths


def test_forager_fraction_grows_with_colony_and_hunger():
    config = SimulationConfig()
    nest = Nest(config, workers=100)
    small = nest.forager_fraction(config, 10)
    large = nest.forager_fraction(config, 1000)
    assert config.nest.min_forager_fraction <= small < large <= config.nest.max_forager_fraction
    nest.hunger = 1.0
    assert nest.forager_fraction(config, 10) > small
    assert nest.forager_fraction(config, 1000) <= config.nest.max_forager_fraction
