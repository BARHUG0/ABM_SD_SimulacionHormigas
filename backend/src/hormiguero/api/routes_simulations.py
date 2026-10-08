from typing import Annotated

from fastapi import APIRouter, Query, Response

from hormiguero.api.dependencies import ManagerDep, SimulationDep
from hormiguero.api.errors import ERROR_RESPONSES
from hormiguero.schemas.config import SimulationConfig
from hormiguero.schemas.metrics import ExportFormat, HistoryKey, HistoryResponse, SurvivalSummary
from hormiguero.schemas.parameters import ParameterUpdate
from hormiguero.schemas.simulation import ControlRequest, SimulationCreate, SimulationInfo, SimulationState
from hormiguero.schemas.state import FieldData, FieldLayer

router = APIRouter(prefix="/simulations", tags=["simulations"], responses=ERROR_RESPONSES)


@router.post("", status_code=201, response_model=SimulationInfo)
async def create_simulation(request: SimulationCreate, manager: ManagerDep) -> SimulationInfo:
    return manager.create(request).info()


@router.get("", response_model=list[SimulationInfo])
async def list_simulations(manager: ManagerDep) -> list[SimulationInfo]:
    return [simulation.info() for simulation in manager.list()]


@router.get("/{simulation_id}", response_model=SimulationInfo)
async def get_simulation_info(simulation: SimulationDep) -> SimulationInfo:
    return simulation.info()


@router.delete("/{simulation_id}", status_code=204)
async def delete_simulation(simulation_id: str, manager: ManagerDep) -> Response:
    manager.delete(simulation_id)
    return Response(status_code=204)


@router.post("/{simulation_id}/control", response_model=SimulationInfo)
async def control_simulation(request: ControlRequest, simulation: SimulationDep) -> SimulationInfo:
    return simulation.control(request)


@router.get("/{simulation_id}/parameters", response_model=SimulationConfig)
async def get_parameters(simulation: SimulationDep) -> SimulationConfig:
    return simulation.config


@router.patch("/{simulation_id}/parameters", response_model=SimulationConfig)
async def update_parameters(request: ParameterUpdate, simulation: SimulationDep) -> SimulationConfig:
    return simulation.update_parameters(request.values)


@router.get("/{simulation_id}/state", response_model=SimulationState)
async def get_state(simulation: SimulationDep) -> SimulationState:
    return simulation.state()


@router.get("/{simulation_id}/fields/{layer}", response_model=FieldData)
async def get_field(
    layer: FieldLayer, simulation: SimulationDep, downsample: Annotated[int, Query(ge=1, le=8)] = 1
) -> FieldData:
    return simulation.field(layer, downsample)


@router.get("/{simulation_id}/history", response_model=HistoryResponse)
async def get_history(
    simulation: SimulationDep,
    keys: Annotated[list[HistoryKey] | None, Query()] = None,
    from_tick: Annotated[int, Query(ge=0)] = 0,
    to_tick: Annotated[int | None, Query(ge=0)] = None,
    every: Annotated[int, Query(ge=1, le=1000)] = 1,
) -> HistoryResponse:
    return simulation.history_query(keys, from_tick, to_tick, every)


@router.get("/{simulation_id}/metrics/summary", response_model=SurvivalSummary)
async def get_summary(simulation: SimulationDep) -> SurvivalSummary:
    return simulation.summary()


@router.get(
    "/{simulation_id}/export",
    response_model=HistoryResponse,
    responses={200: {"content": {"text/csv": {"schema": {"type": "string"}}}}},
)
async def export_history(
    simulation: SimulationDep, format: Annotated[ExportFormat, Query()] = ExportFormat.CSV
) -> HistoryResponse | Response:
    if format is ExportFormat.JSON:
        return simulation.history_query(None, 0, None, 1)
    return Response(
        content=simulation.history.to_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{simulation.id}.csv"'},
    )
