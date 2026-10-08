from enum import StrEnum

from hormiguero.schemas.common import ApiModel
from hormiguero.schemas.state import DeathsByCause


class HistoryKey(StrEnum):
    STOCKS_FOOD = "stocks.food"
    STOCKS_EGGS = "stocks.eggs"
    STOCKS_LARVAE = "stocks.larvae"
    STOCKS_WORKERS = "stocks.workers"
    FLOWS_FOOD_INCOME = "flows.food_income"
    FLOWS_CONSUMPTION = "flows.consumption"
    FLOWS_EGG_LAYING = "flows.egg_laying"
    FLOWS_HATCHING = "flows.hatching"
    FLOWS_MATURATION = "flows.maturation"
    FLOWS_MORTALITY = "flows.mortality"
    NEST_FORAGER_FRACTION = "nest.forager_fraction"
    METRICS_ALIVE_ANTS = "metrics.alive_ants"
    METRICS_FORAGERS_ACTIVE = "metrics.foragers_active"
    METRICS_ANTS_IN_NEST = "metrics.ants_in_nest"
    METRICS_PREDATORS = "metrics.predators"
    METRICS_FOOD_IN_WORLD = "metrics.food_in_world"
    METRICS_FOOD_DELIVERED_TOTAL = "metrics.food_delivered_total"
    METRICS_FORAGING_EFFICIENCY = "metrics.foraging_efficiency"


class ExportFormat(StrEnum):
    CSV = "csv"
    JSON = "json"


class HistoryResponse(ApiModel):
    keys: list[HistoryKey]
    ticks: list[int]
    series: dict[str, list[float]]


class RecoveryInfo(ApiModel):
    event_id: str
    population_before: float
    min_population_during: float
    recovery_ticks: int | None


class SurvivalSummary(ApiModel):
    ticks_elapsed: int
    colony_alive: bool
    collapse_tick: int | None
    peak_population: float
    min_population: float
    min_population_tick: int
    mean_foraging_efficiency: float
    total_food_delivered: float
    deaths: DeathsByCause
    recoveries: list[RecoveryInfo]
