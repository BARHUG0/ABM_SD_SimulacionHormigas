from hormiguero.errors import unprocessable
from hormiguero.schemas.common import Region
from hormiguero.schemas.config import (
    AntConfig,
    NestConfig,
    PheromoneConfig,
    PredatorConfig,
    SimulationConfig,
    WorldConfig,
)
from hormiguero.schemas.events import EventCreate, PerturbationType
from hormiguero.schemas.simulation import ScenarioInfo

def calibrated_config(predators: PredatorConfig | None = None) -> SimulationConfig:
    return SimulationConfig(
        world=WorldConfig(food_sources=12, food_source_radius=8, food_regen_rate=3.0),
        pheromones=PheromoneConfig(food_evaporation=0.005, home_evaporation=0.005),
        ants=AntConfig(speed=2.0, energy_decay=0.45),
        predators=predators or PredatorConfig(),
        nest=NestConfig(
            initial_food=1000.0,
            worker_consumption=0.005,
            larva_consumption=0.01,
            max_egg_laying_rate=0.05,
            starvation_mortality=0.002,
        ),
    )


SCENARIOS = {
    scenario.id: scenario
    for scenario in [
        ScenarioInfo(
            id="baseline",
            name="Colonia base",
            description="Colonia sin perturbaciones, útil como referencia",
            config=calibrated_config(),
            events=[],
        ),
        ScenarioInfo(
            id="drought",
            name="Sequía prolongada",
            description="Una sequía intensa reduce la comida disponible a mitad de la simulación",
            config=calibrated_config(),
            events=[EventCreate(type=PerturbationType.DROUGHT, intensity=0.9, duration=3000, start_tick=6000)],
        ),
        ScenarioInfo(
            id="flood",
            name="Inundación",
            description="El agua cubre la zona central del mundo durante un periodo corto",
            config=calibrated_config(),
            events=[
                EventCreate(
                    type=PerturbationType.FLOOD,
                    intensity=0.5,
                    duration=150,
                    start_tick=5000,
                    region=Region(x=100, y=100, width=80, height=80),
                )
            ],
        ),
        ScenarioInfo(
            id="predator_invasion",
            name="Invasión de depredadores",
            description="Más depredadores desde el inicio y una oleada adicional",
            config=calibrated_config(
                PredatorConfig(initial_count=2, speed=2.0, vision_radius=10.0, attack_probability=0.6, energy_decay=0.1, energy_gain_per_kill=30.0)
            ),
            events=[EventCreate(type=PerturbationType.PREDATOR_WAVE, predator_count=30, duration=5000, start_tick=3000)],
        ),
    ]
}


def get_scenario(scenario_id: str) -> ScenarioInfo:
    if scenario_id not in SCENARIOS:
        raise unprocessable("unknown_scenario", f"Escenario '{scenario_id}' no existe", {"available": list(SCENARIOS)})
    return SCENARIOS[scenario_id]
