import secrets

from hormiguero.engine.scenarios import get_scenario
from hormiguero.engine.simulation import Simulation, new_id
from hormiguero.errors import conflict, not_found
from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.simulation import SimulationCreate

MAX_SIMULATIONS = 8


class SimulationManager:
    def __init__(self):
        self.simulations: dict[str, Simulation] = {}

    def create(self, request: SimulationCreate) -> Simulation:
        if len(self.simulations) >= MAX_SIMULATIONS:
            raise conflict("simulation_limit", f"Máximo de {MAX_SIMULATIONS} simulaciones simultáneas")
        scenario = get_scenario(request.scenario_id) if request.scenario_id else None
        config = scenario.config if scenario else request.config or SimulationConfig()
        seed = request.seed if request.seed is not None else secrets.randbelow(2**32)
        simulation = Simulation(
            sim_id=new_id("sim"),
            name=request.name or (scenario.name if scenario else f"Simulación {len(self.simulations) + 1}"),
            config=config,
            seed=seed,
            scenario=scenario,
        )
        self.simulations[simulation.id] = simulation
        return simulation

    def get(self, simulation_id: str) -> Simulation:
        if simulation_id not in self.simulations:
            raise not_found("simulation", simulation_id)
        return self.simulations[simulation_id]

    def list(self) -> list[Simulation]:
        return list(self.simulations.values())

    def delete(self, simulation_id: str) -> None:
        self.get(simulation_id).close()
        del self.simulations[simulation_id]

    def shutdown(self) -> None:
        for simulation in self.simulations.values():
            simulation.close()
        self.simulations.clear()
