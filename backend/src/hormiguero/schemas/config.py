from typing import Any, Self

from pydantic import Field, model_validator

from hormiguero.schemas.common import ApiModel


def param(default: Any, *, ge: float, le: float, unit: str = "", live: bool = False, description: str = "") -> Any:
    return Field(
        default,
        ge=ge,
        le=le,
        description=description,
        json_schema_extra={"unit": unit, "live_editable": live},
    )


class RunConfig(ApiModel):
    dt: float = param(1.0, ge=0.01, le=10.0, unit="tick", description="Paso de integración del modelo SD")
    max_ticks: int = param(20000, ge=100, le=1_000_000, unit="ticks", live=True, description="Duración máxima de la simulación")


class WorldConfig(ApiModel):
    width: int = param(200, ge=50, le=400, unit="celdas", description="Ancho del mundo")
    height: int = param(200, ge=50, le=400, unit="celdas", description="Alto del mundo")
    nest_x: int = param(100, ge=0, le=399, unit="celda", description="Columna del centro del nido")
    nest_y: int = param(100, ge=0, le=399, unit="celda", description="Fila del centro del nido")
    nest_radius: int = param(5, ge=1, le=20, unit="celdas", description="Radio del nido")
    food_sources: int = param(3, ge=0, le=20, unit="fuentes", description="Fuentes de comida iniciales")
    food_per_source: float = param(500.0, ge=10, le=5000, unit="unidades", description="Comida en cada fuente inicial")
    food_source_radius: int = param(6, ge=1, le=30, unit="celdas", description="Radio de cada fuente de comida")
    food_regen_rate: float = param(0.0, ge=0, le=10, unit="unidades/tick", live=True, description="Regeneración de comida en las fuentes")

    @model_validator(mode="after")
    def nest_inside_world(self) -> Self:
        fits_x = self.nest_radius <= self.nest_x < self.width - self.nest_radius
        fits_y = self.nest_radius <= self.nest_y < self.height - self.nest_radius
        if not (fits_x and fits_y):
            raise ValueError("El nido debe quedar completamente dentro del mundo")
        return self


class PheromoneConfig(ApiModel):
    food_evaporation: float = param(0.02, ge=0, le=1, unit="fracción/tick", live=True, description="Evaporación del rastro hacia la comida")
    home_evaporation: float = param(0.01, ge=0, le=1, unit="fracción/tick", live=True, description="Evaporación del rastro hacia el nido")
    alarm_evaporation: float = param(0.05, ge=0, le=1, unit="fracción/tick", live=True, description="Evaporación de la feromona de alarma")
    diffusion: float = param(0.1, ge=0, le=1, unit="fracción/tick", live=True, description="Difusión de feromonas a celdas vecinas")
    deposit_amount: float = param(1.0, ge=0, le=10, unit="unidades", live=True, description="Feromona depositada por hormiga y tick")


class AntConfig(ApiModel):
    initial_workers: int = param(100, ge=0, le=2000, unit="hormigas", description="Obreras iniciales")
    max_ants: int = param(2000, ge=10, le=5000, unit="hormigas", description="Población máxima de agentes")
    speed: float = param(1.0, ge=0.1, le=3, unit="celdas/tick", live=True, description="Velocidad de las hormigas")
    sensor_angle: float = param(45.0, ge=5, le=90, unit="grados", live=True, description="Ángulo de los sensores de feromona")
    sensor_distance: float = param(3.0, ge=1, le=10, unit="celdas", live=True, description="Distancia de los sensores de feromona")
    random_turn: float = param(15.0, ge=0, le=90, unit="grados", live=True, description="Giro aleatorio máximo por tick")
    carry_capacity: float = param(1.0, ge=0.1, le=5, unit="unidades", live=True, description="Comida que carga una hormiga")
    energy_max: float = param(100.0, ge=10, le=1000, unit="energía", description="Energía máxima de una hormiga")
    energy_decay: float = param(0.1, ge=0, le=5, unit="energía/tick", live=True, description="Gasto de energía por tick")
    lifespan: int = param(5000, ge=100, le=100_000, unit="ticks", live=True, description="Esperanza de vida de una obrera")
    soldier_fraction: float = param(0.1, ge=0, le=0.5, unit="fracción", live=True, description="Fracción de nuevas hormigas que nacen soldado")


class PredatorConfig(ApiModel):
    initial_count: int = param(2, ge=0, le=50, unit="depredadores", description="Depredadores iniciales")
    max_predators: int = param(50, ge=1, le=100, unit="depredadores", description="Máximo de depredadores simultáneos")
    speed: float = param(0.8, ge=0.1, le=3, unit="celdas/tick", live=True, description="Velocidad de los depredadores")
    vision_radius: float = param(8.0, ge=1, le=30, unit="celdas", live=True, description="Radio de visión")
    attack_probability: float = param(0.3, ge=0, le=1, unit="probabilidad", live=True, description="Probabilidad de capturar una hormiga cercana")
    energy_gain_per_kill: float = param(20.0, ge=0, le=200, unit="energía", live=True, description="Energía ganada por captura")
    energy_decay: float = param(0.2, ge=0, le=5, unit="energía/tick", live=True, description="Gasto de energía por tick")


class NestConfig(ApiModel):
    initial_food: float = param(200.0, ge=0, le=10000, unit="unidades", description="Comida inicial almacenada")
    initial_eggs: float = param(20.0, ge=0, le=2000, unit="huevos", description="Huevos iniciales")
    initial_larvae: float = param(20.0, ge=0, le=2000, unit="larvas", description="Larvas iniciales")
    worker_consumption: float = param(0.01, ge=0, le=1, unit="unidades/obrera/tick", live=True, description="Consumo de comida por obrera")
    larva_consumption: float = param(0.02, ge=0, le=1, unit="unidades/larva/tick", live=True, description="Consumo de comida por larva")
    max_egg_laying_rate: float = param(0.5, ge=0, le=10, unit="huevos/tick", live=True, description="Puesta máxima de la reina")
    food_half_saturation: float = param(100.0, ge=1, le=5000, unit="unidades", live=True, description="Comida a la que la puesta llega a la mitad del máximo")
    egg_duration: float = param(200.0, ge=1, le=5000, unit="ticks", live=True, description="Tiempo medio de incubación")
    larva_duration: float = param(400.0, ge=1, le=5000, unit="ticks", live=True, description="Tiempo medio de maduración de larva a obrera")
    starvation_mortality: float = param(0.01, ge=0, le=1, unit="fracción/tick", live=True, description="Mortalidad cuando no hay comida")
    min_forager_fraction: float = param(0.2, ge=0, le=1, unit="fracción", live=True, description="Fracción de forrajeo en colonias pequeñas")
    max_forager_fraction: float = param(0.8, ge=0, le=1, unit="fracción", live=True, description="Fracción de forrajeo en colonias grandes")
    colony_size_half_saturation: float = param(200.0, ge=1, le=5000, unit="obreras", live=True, description="Tamaño de colonia con fracción de forrajeo intermedia")

    @model_validator(mode="after")
    def forager_bounds_ordered(self) -> Self:
        if self.min_forager_fraction > self.max_forager_fraction:
            raise ValueError("min_forager_fraction no puede superar a max_forager_fraction")
        return self


class SimulationConfig(ApiModel):
    run: RunConfig = Field(default_factory=RunConfig)
    world: WorldConfig = Field(default_factory=WorldConfig)
    pheromones: PheromoneConfig = Field(default_factory=PheromoneConfig)
    ants: AntConfig = Field(default_factory=AntConfig)
    predators: PredatorConfig = Field(default_factory=PredatorConfig)
    nest: NestConfig = Field(default_factory=NestConfig)
