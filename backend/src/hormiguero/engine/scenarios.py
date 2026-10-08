from hormiguero.errors import unprocessable
from hormiguero.schemas.common import Region
from hormiguero.schemas.config import PredatorConfig, SimulationConfig
from hormiguero.schemas.events import EventCreate, PerturbationType
from hormiguero.schemas.simulation import ScenarioInfo

SCENARIOS = {
    scenario.id: scenario
    for scenario in [
        ScenarioInfo(
            id="baseline",
            name="Colonia base",
            description="Colonia sin perturbaciones, útil como referencia",
            config=SimulationConfig(),
            events=[],
        ),
        ScenarioInfo(
            id="drought",
            name="Sequía prolongada",
            description="Una sequía intensa reduce la comida disponible a mitad de la simulación",
            config=SimulationConfig(),
            events=[EventCreate(type=PerturbationType.DROUGHT, intensity=0.7, duration=2000, start_tick=1000)],
        ),
        ScenarioInfo(
            id="flood",
            name="Inundación",
            description="El agua cubre la zona central del mundo durante un periodo corto",
            config=SimulationConfig(),
            events=[
                EventCreate(
                    type=PerturbationType.FLOOD,
                    intensity=0.8,
                    duration=300,
                    start_tick=800,
                    region=Region(x=60, y=60, width=80, height=80),
                )
            ],
        ),
        ScenarioInfo(
            id="predator_invasion",
            name="Invasión de depredadores",
            description="Más depredadores desde el inicio y una oleada adicional",
            config=SimulationConfig(predators=PredatorConfig(initial_count=5)),
            events=[EventCreate(type=PerturbationType.PREDATOR_WAVE, predator_count=15, duration=1000, start_tick=500)],
        ),
    ]
}


def get_scenario(scenario_id: str) -> ScenarioInfo:
    if scenario_id not in SCENARIOS:
        raise unprocessable("unknown_scenario", f"Escenario '{scenario_id}' no existe", {"available": list(SCENARIOS)})
    return SCENARIOS[scenario_id]
