from typing import Any

from fastapi import APIRouter
from pydantic import TypeAdapter

from hormiguero import API_VERSION
from hormiguero.engine.parameters import PARAMETER_SPECS
from hormiguero.engine.scenarios import SCENARIOS
from hormiguero.schemas.common import ApiModel, HealthResponse
from hormiguero.schemas.messages import ClientMessage, ServerMessage
from hormiguero.schemas.parameters import ParameterSpec
from hormiguero.schemas.simulation import ScenarioInfo

router = APIRouter(tags=["meta"])


class WsSchemaResponse(ApiModel):
    server: dict[str, Any]
    client: dict[str, Any]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=API_VERSION)


@router.get("/parameters/schema", response_model=list[ParameterSpec])
async def parameter_schema() -> list[ParameterSpec]:
    return list(PARAMETER_SPECS.values())


@router.get("/scenarios", response_model=list[ScenarioInfo])
async def list_scenarios() -> list[ScenarioInfo]:
    return list(SCENARIOS.values())


@router.get("/ws/schema", response_model=WsSchemaResponse)
async def websocket_schema() -> WsSchemaResponse:
    return WsSchemaResponse(
        server=TypeAdapter(ServerMessage).json_schema(mode="serialization"),
        client=TypeAdapter(ClientMessage).json_schema(mode="validation"),
    )
