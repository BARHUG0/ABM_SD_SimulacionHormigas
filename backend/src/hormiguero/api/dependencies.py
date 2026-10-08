from typing import Annotated

from fastapi import Depends, Request

from hormiguero.engine.manager import SimulationManager
from hormiguero.engine.simulation import Simulation


async def get_manager(request: Request) -> SimulationManager:
    return request.app.state.manager


ManagerDep = Annotated[SimulationManager, Depends(get_manager)]


async def get_simulation(simulation_id: str, manager: ManagerDep) -> Simulation:
    return manager.get(simulation_id)


SimulationDep = Annotated[Simulation, Depends(get_simulation)]
