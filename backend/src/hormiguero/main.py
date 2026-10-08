from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hormiguero import API_VERSION
from hormiguero.api import routes_events, routes_meta, routes_simulations, routes_world, ws
from hormiguero.api.errors import install_error_handlers
from hormiguero.api.openapi import build_openapi
from hormiguero.engine.manager import SimulationManager

API_PREFIX = "/api/v1"
CORS_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173"]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    app.state.manager.shutdown()


def create_app() -> FastAPI:
    app = FastAPI(
        title="Hormiguero Vivo API",
        version=API_VERSION,
        description="Simulación híbrida ABM + SD de una colonia de hormigas",
        lifespan=lifespan,
    )
    app.state.manager = SimulationManager()
    app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])
    install_error_handlers(app)
    for module in (routes_meta, routes_simulations, routes_world, routes_events, ws):
        app.include_router(module.router, prefix=API_PREFIX)
    app.openapi = lambda: build_openapi(app)
    return app


app = create_app()
