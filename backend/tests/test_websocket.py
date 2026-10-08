import pytest
from starlette.websockets import WebSocketDisconnect

from conftest import API

from hormiguero.schemas.messages import ServerMessage


def stream(client, simulation_id):
    return client.websocket_connect(f"{API}/ws/simulations/{simulation_id}")


def receive_until(websocket, message_type, limit=50):
    for _ in range(limit):
        message = websocket.receive_json()
        ServerMessage.model_validate(message)
        if message["type"] == message_type:
            return message
    raise AssertionError(f"No llegó un mensaje {message_type}")


def test_greeting_sequence(client, simulation_id):
    with stream(client, simulation_id) as websocket:
        init = websocket.receive_json()
        assert init["type"] == "init"
        assert init["payload"]["world"]["width"] == 200
        assert websocket.receive_json()["type"] == "status"
        assert websocket.receive_json()["type"] == "frame"
        layers = {websocket.receive_json()["payload"]["layer"] for _ in range(3)}
        assert layers == {"pheromone_food", "pheromone_home", "food"}


def test_rest_step_streams_frames(client, simulation_id):
    with stream(client, simulation_id) as websocket:
        receive_until(websocket, "frame")
        client.post(f"{API}/simulations/{simulation_id}/control", json={"action": "step", "steps": 2})
        frame = receive_until(websocket, "frame")
        assert frame["tick"] == 1
        assert len(frame["payload"]["ants"]["ids"]) == 100


def test_subscribe_changes_layers(client, simulation_id):
    with stream(client, simulation_id) as websocket:
        receive_until(websocket, "frame")
        websocket.send_json({"type": "subscribe", "payload": {"layers": ["water"], "field_downsample": 4}})
        field = receive_until(websocket, "field")
        while field["payload"]["layer"] != "water":
            field = receive_until(websocket, "field")
        assert field["payload"]["width"] == 50


def test_ping_and_invalid_message(client, simulation_id):
    with stream(client, simulation_id) as websocket:
        websocket.send_json({"type": "ping"})
        receive_until(websocket, "pong")
        websocket.send_json({"type": "dance"})
        error = receive_until(websocket, "error")
        assert error["payload"]["code"] == "invalid_message"


def test_notices_for_world_edits(client, simulation_id):
    with stream(client, simulation_id) as websocket:
        receive_until(websocket, "frame")
        ack = client.post(f"{API}/simulations/{simulation_id}/world/food", json={"x": 5, "y": 5}).json()
        notice = receive_until(websocket, "event")
        assert notice["payload"]["kind"] == "command_applied"
        assert notice["payload"]["command_id"] == ack["command_id"]


def test_unknown_simulation_closes_socket(client):
    with stream(client, "sim_missing") as websocket:
        assert websocket.receive_json()["payload"]["code"] == "simulation_not_found"
        with pytest.raises(WebSocketDisconnect) as closed:
            websocket.receive_json()
        assert closed.value.code == 4404


def test_deleting_simulation_closes_stream(client, simulation_id):
    with stream(client, simulation_id) as websocket:
        receive_until(websocket, "frame")
        client.delete(f"{API}/simulations/{simulation_id}")
        with pytest.raises(WebSocketDisconnect):
            for _ in range(20):
                websocket.receive_json()
