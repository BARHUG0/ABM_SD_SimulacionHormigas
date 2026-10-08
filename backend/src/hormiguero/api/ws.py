import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from hormiguero.engine.simulation import Simulation, Subscriber
from hormiguero.schemas.common import ErrorBody
from hormiguero.schemas.messages import ClientMessage, ErrorMessage, PingMessage, SubscribeMessage

router = APIRouter()

CLOSE_NOT_FOUND = 4404
CLOSE_GOING_AWAY = 1001


@router.websocket("/ws/simulations/{simulation_id}")
async def simulation_stream(websocket: WebSocket, simulation_id: str) -> None:
    await websocket.accept()
    simulation = websocket.app.state.manager.simulations.get(simulation_id)
    if simulation is None:
        error = ErrorBody(code="simulation_not_found", message=f"Simulación '{simulation_id}' no encontrada")
        message = ErrorMessage(type="error", seq=1, tick=0, sim_time=0.0, payload=error)
        await websocket.send_json(message.model_dump(mode="json"))
        await websocket.close(code=CLOSE_NOT_FOUND)
        return

    subscriber = Subscriber()
    simulation.attach(subscriber)
    tasks = {
        asyncio.create_task(_send_loop(websocket, subscriber)),
        asyncio.create_task(_receive_loop(websocket, simulation, subscriber)),
    }
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        simulation.detach(subscriber)
        for task in tasks:
            task.cancel()


async def _send_loop(websocket: WebSocket, subscriber: Subscriber) -> None:
    try:
        while (message := await subscriber.queue.get()) is not None:
            await websocket.send_json(message)
        await websocket.close(code=CLOSE_GOING_AWAY)
    except (WebSocketDisconnect, RuntimeError):
        return


async def _receive_loop(websocket: WebSocket, simulation: Simulation, subscriber: Subscriber) -> None:
    try:
        while True:
            text = await websocket.receive_text()
            try:
                message = ClientMessage.model_validate_json(text).root
            except ValidationError as error:
                details = error.errors(include_url=False, include_context=False, include_input=False)
                simulation.send_error(
                    subscriber, ErrorBody(code="invalid_message", message="Mensaje no válido", details=details)
                )
                continue
            if isinstance(message, SubscribeMessage):
                simulation.update_subscription(subscriber, message.payload)
            elif isinstance(message, PingMessage):
                simulation.send_pong(subscriber)
    except WebSocketDisconnect:
        return
