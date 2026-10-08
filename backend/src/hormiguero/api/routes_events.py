from fastapi import APIRouter

from hormiguero.api.dependencies import SimulationDep
from hormiguero.api.errors import ERROR_RESPONSES
from hormiguero.schemas.events import EventCreate, EventInfo

router = APIRouter(prefix="/simulations/{simulation_id}/events", tags=["events"], responses=ERROR_RESPONSES)


@router.post("", status_code=201, response_model=EventInfo)
async def create_event(request: EventCreate, simulation: SimulationDep) -> EventInfo:
    return simulation.add_event(request)


@router.get("", response_model=list[EventInfo])
async def list_events(simulation: SimulationDep) -> list[EventInfo]:
    return list(simulation.events.values())


@router.get("/{event_id}", response_model=EventInfo)
async def get_event(event_id: str, simulation: SimulationDep) -> EventInfo:
    return simulation.get_event(event_id)


@router.delete("/{event_id}", response_model=EventInfo)
async def cancel_event(event_id: str, simulation: SimulationDep) -> EventInfo:
    return simulation.cancel_event(event_id)
