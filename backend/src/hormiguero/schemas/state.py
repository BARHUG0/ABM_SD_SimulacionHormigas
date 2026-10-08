from enum import StrEnum
from typing import Literal

from pydantic import Field

from hormiguero.schemas.common import ApiModel


class AntRole(StrEnum):
    FORAGER = "forager"
    SCOUT = "scout"
    SOLDIER = "soldier"


class AntState(StrEnum):
    SEARCHING = "searching"
    RETURNING = "returning"
    FLEEING = "fleeing"
    IDLE_IN_NEST = "idle_in_nest"


class PredatorState(StrEnum):
    WANDERING = "wandering"
    HUNTING = "hunting"
    EATING = "eating"


class PredatorSource(StrEnum):
    INITIAL = "initial"
    USER = "user"
    WAVE = "wave"


class FieldLayer(StrEnum):
    PHEROMONE_FOOD = "pheromone_food"
    PHEROMONE_HOME = "pheromone_home"
    PHEROMONE_ALARM = "pheromone_alarm"
    FOOD = "food"
    OBSTACLES = "obstacles"
    WATER = "water"
    MOISTURE = "moisture"


class AntsFrame(ApiModel):
    ids: list[int]
    x: list[float]
    y: list[float]
    heading: list[float] = Field(description="Radianes")
    role: list[int] = Field(description="Índice en Catalog.ant_roles")
    state: list[int] = Field(description="Índice en Catalog.ant_states")
    carrying: list[bool]
    energy: list[float]
    age: list[int] = Field(description="Ticks de vida")


class PredatorsFrame(ApiModel):
    ids: list[int]
    x: list[float]
    y: list[float]
    heading: list[float]
    state: list[PredatorState]
    energy: list[float]
    source: list[PredatorSource]


class NestStocks(ApiModel):
    food: float
    eggs: float
    larvae: float
    workers: float


class NestFlows(ApiModel):
    food_income: float
    consumption: float
    egg_laying: float
    hatching: float
    maturation: float
    mortality: float


class NestFrame(ApiModel):
    stocks: NestStocks
    flows: NestFlows
    forager_fraction: float


class DeathsByCause(ApiModel):
    predator: int = 0
    flood: int = 0
    starvation: int = 0
    old_age: int = 0


class FrameMetrics(ApiModel):
    alive_ants: int
    foragers_active: int
    ants_in_nest: int
    predators: int
    food_in_world: float
    food_delivered_total: float
    foraging_efficiency: float = Field(description="Comida entregada por hormiga activa y tick")
    deaths: DeathsByCause


class FrameData(ApiModel):
    ants: AntsFrame = Field(description="Arreglos paralelos: el índice i describe a la misma hormiga en cada lista")
    predators: PredatorsFrame
    nest: NestFrame
    metrics: FrameMetrics
    active_event_ids: list[str]


class FieldData(ApiModel):
    layer: FieldLayer
    width: int
    height: int
    downsample: int
    encoding: Literal["uint8_base64"]
    scale: float = Field(
        description="Valor real = byte / 255 * scale. Es el máximo histórico de la capa, estable entre envíos hasta un reset"
    )
    data: str = Field(description="Bytes uint8 en base64, fila por fila, de largo width * height")


class NestGeometry(ApiModel):
    x: int
    y: int
    radius: int


class WorldStatic(ApiModel):
    width: int
    height: int
    nest: NestGeometry
    obstacles: FieldData
