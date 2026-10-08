from fastapi import APIRouter

from hormiguero.api.dependencies import SimulationDep
from hormiguero.api.errors import ERROR_RESPONSES
from hormiguero.schemas.common import CommandAck
from hormiguero.schemas.world import BrushStroke, FoodPlacement, PredatorPlacement, PredatorsCreated

router = APIRouter(prefix="/simulations/{simulation_id}", tags=["world"], responses=ERROR_RESPONSES)


@router.post("/world/obstacles", response_model=CommandAck)
async def paint_obstacles(stroke: BrushStroke, simulation: SimulationDep) -> CommandAck:
    return simulation.paint_obstacles(stroke)


@router.post("/world/food", response_model=CommandAck)
async def place_food(placement: FoodPlacement, simulation: SimulationDep) -> CommandAck:
    return simulation.add_food(placement)


@router.post("/predators", status_code=201, response_model=PredatorsCreated)
async def place_predators(placement: PredatorPlacement, simulation: SimulationDep) -> PredatorsCreated:
    return simulation.add_predators(placement)


@router.delete("/predators/{predator_id}", response_model=CommandAck)
async def remove_predator(predator_id: int, simulation: SimulationDep) -> CommandAck:
    return simulation.remove_predator(predator_id)
