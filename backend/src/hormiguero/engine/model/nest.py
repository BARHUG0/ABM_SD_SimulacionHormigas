import math

from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.state import NestFlows, NestStocks

from .types import NestReport

HUNGER_RESPONSE = 0.3


class Nest:
    def __init__(self, config: SimulationConfig, workers: int) -> None:
        nest = config.nest
        self.stocks = NestStocks(
            food=nest.initial_food,
            eggs=nest.initial_eggs,
            larvae=nest.initial_larvae,
            workers=float(workers),
        )
        self.flows = NestFlows(
            food_income=0.0,
            consumption=0.0,
            egg_laying=0.0,
            hatching=0.0,
            maturation=0.0,
            mortality=0.0,
        )
        self.hunger = 0.0
        self.maturation_carry = 0.0
        self.starvation_carry = 0.0

    def forager_fraction(self, config: SimulationConfig, workers: int) -> float:
        nest = config.nest
        saturation = workers / (workers + nest.colony_size_half_saturation)
        base = nest.min_forager_fraction + (nest.max_forager_fraction - nest.min_forager_fraction) * saturation
        return min(nest.max_forager_fraction, base + HUNGER_RESPONSE * self.hunger)

    def step(self, config: SimulationConfig, delivered_food: float, workers: int, ant_deaths: int) -> NestReport:
        nest = config.nest
        dt = config.run.dt
        food, eggs, larvae = self.stocks.food, self.stocks.eggs, self.stocks.larvae

        income = delivered_food / dt
        demand = workers * nest.worker_consumption + larvae * nest.larva_consumption
        consumption = min(demand, food / dt + income)
        hunger = (demand - consumption) / demand if demand > 0 else 0.0
        laying = nest.max_egg_laying_rate * food / (food + nest.food_half_saturation)
        hatching = eggs / nest.egg_duration
        maturation = larvae / nest.larva_duration
        larva_deaths = nest.starvation_mortality * hunger * larvae
        worker_deaths = nest.starvation_mortality * hunger * workers

        self.maturation_carry += maturation * dt
        self.starvation_carry += worker_deaths * dt
        capacity = max(0, config.ants.max_ants - workers)
        new_workers = min(math.floor(self.maturation_carry), capacity, math.floor(larvae))
        self.maturation_carry = min(self.maturation_carry - new_workers, larvae - new_workers)
        starvation_deaths = min(math.floor(self.starvation_carry), workers)
        self.starvation_carry -= starvation_deaths

        self.hunger = hunger
        self.stocks = NestStocks(
            food=max(food + (income - consumption) * dt, 0.0),
            eggs=max(eggs + (laying - hatching) * dt, 0.0),
            larvae=max(larvae + (hatching - larva_deaths) * dt - new_workers, 0.0),
            workers=float(workers),
        )
        self.flows = NestFlows(
            food_income=income,
            consumption=consumption,
            egg_laying=laying,
            hatching=hatching,
            maturation=new_workers / dt,
            mortality=(ant_deaths + starvation_deaths) / dt,
        )
        return NestReport(new_workers=new_workers, starvation_deaths=starvation_deaths)

    def return_larvae(self, count: int) -> None:
        if count <= 0:
            return
        self.stocks = self.stocks.model_copy(update={"larvae": self.stocks.larvae + count})
