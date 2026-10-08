from enum import StrEnum

from hormiguero.schemas.catalog import Catalog, CatalogEntry
from hormiguero.schemas.events import PerturbationType
from hormiguero.schemas.metrics import HistoryKey
from hormiguero.schemas.state import AntRole, AntState, FieldLayer, PredatorSource, PredatorState

SERIES = {
    HistoryKey.STOCKS_FOOD: ("Comida almacenada", "unidades"),
    HistoryKey.STOCKS_EGGS: ("Huevos", "huevos"),
    HistoryKey.STOCKS_LARVAE: ("Larvas", "larvas"),
    HistoryKey.STOCKS_WORKERS: ("Obreras", "hormigas"),
    HistoryKey.FLOWS_FOOD_INCOME: ("Ingreso de comida", "unidades/tick"),
    HistoryKey.FLOWS_CONSUMPTION: ("Consumo de comida", "unidades/tick"),
    HistoryKey.FLOWS_EGG_LAYING: ("Puesta de huevos", "huevos/tick"),
    HistoryKey.FLOWS_HATCHING: ("Eclosión", "larvas/tick"),
    HistoryKey.FLOWS_MATURATION: ("Maduración", "obreras/tick"),
    HistoryKey.FLOWS_MORTALITY: ("Mortalidad", "hormigas/tick"),
    HistoryKey.NEST_FORAGER_FRACTION: ("Fracción de forrajeo", "fracción"),
    HistoryKey.METRICS_ALIVE_ANTS: ("Hormigas vivas", "hormigas"),
    HistoryKey.METRICS_FORAGERS_ACTIVE: ("Hormigas fuera del nido", "hormigas"),
    HistoryKey.METRICS_ANTS_IN_NEST: ("Hormigas en el nido", "hormigas"),
    HistoryKey.METRICS_PREDATORS: ("Depredadores", "depredadores"),
    HistoryKey.METRICS_FOOD_IN_WORLD: ("Comida en el mundo", "unidades"),
    HistoryKey.METRICS_FOOD_DELIVERED_TOTAL: ("Comida entregada acumulada", "unidades"),
    HistoryKey.METRICS_FORAGING_EFFICIENCY: ("Eficiencia de forrajeo", "unidades/hormiga/tick"),
    HistoryKey.DEATHS_PREDATOR: ("Muertes por depredador", "hormigas"),
    HistoryKey.DEATHS_FLOOD: ("Muertes por inundación", "hormigas"),
    HistoryKey.DEATHS_STARVATION: ("Muertes por hambre", "hormigas"),
    HistoryKey.DEATHS_OLD_AGE: ("Muertes por vejez", "hormigas"),
}

LAYERS = {
    FieldLayer.PHEROMONE_FOOD: ("Feromona hacia comida", "unidades"),
    FieldLayer.PHEROMONE_HOME: ("Feromona hacia el nido", "unidades"),
    FieldLayer.PHEROMONE_ALARM: ("Feromona de alarma", "unidades"),
    FieldLayer.FOOD: ("Comida", "unidades"),
    FieldLayer.OBSTACLES: ("Obstáculos", "0 o 1"),
    FieldLayer.WATER: ("Agua", "intensidad"),
    FieldLayer.MOISTURE: ("Humedad", "fracción"),
}

LABELS: dict[StrEnum, str] = {
    AntRole.FORAGER: "Recolectora",
    AntRole.SCOUT: "Exploradora",
    AntRole.SOLDIER: "Soldado",
    AntState.SEARCHING: "Buscando comida",
    AntState.RETURNING: "Regresando con comida",
    AntState.FLEEING: "Huyendo",
    AntState.IDLE_IN_NEST: "En el nido",
    PredatorState.WANDERING: "Merodeando",
    PredatorState.HUNTING: "Cazando",
    PredatorState.EATING: "Comiendo",
    PredatorSource.INITIAL: "Inicial",
    PredatorSource.USER: "Colocado por el usuario",
    PredatorSource.WAVE: "Oleada",
    PerturbationType.DROUGHT: "Sequía",
    PerturbationType.FLOOD: "Inundación",
    PerturbationType.PREDATOR_WAVE: "Oleada de depredadores",
}


def _entries(mapping: dict) -> list[CatalogEntry]:
    return [CatalogEntry(value=key.value, label=label, unit=unit) for key, (label, unit) in mapping.items()]


def _labels(enum: type[StrEnum]) -> list[CatalogEntry]:
    return [CatalogEntry(value=member.value, label=LABELS[member], unit="") for member in enum]


CATALOG = Catalog(
    series=_entries(SERIES),
    layers=_entries(LAYERS),
    ant_roles=_labels(AntRole),
    ant_states=_labels(AntState),
    predator_states=_labels(PredatorState),
    predator_sources=_labels(PredatorSource),
    perturbations=_labels(PerturbationType),
)
