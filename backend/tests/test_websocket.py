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


def test_messages_carry_consecutive_seq(client, simulation_id):
    with stream(client, simulation_id) as websocket:
        seqs = [websocket.receive_json()["seq"] for _ in range(6)]
        assert seqs == [1, 2, 3, 4, 5, 6]


def test_world_edits_stream_frame_and_layer_while_paused(client, simulation_id):
    with stream(client, simulation_id) as websocket:
        receive_until(websocket, "frame")
        for _ in range(3):
            receive_until(websocket, "field")
        client.post(f"{API}/simulations/{simulation_id}/world/food", json={"x": 5, "y": 5})
        assert websocket.receive_json()["type"] == "frame"
        field = websocket.receive_json()
        assert field["type"] == "field" and field["payload"]["layer"] == "food"
        client.post(f"{API}/simulations/{simulation_id}/predators", json={"x": 5, "y": 5, "count": 1})
        frame = receive_until(websocket, "frame")
        assert len(frame["payload"]["predators"]["ids"]) == 3


def test_parameter_update_streams_config(client, simulation_id):
    with stream(client, simulation_id) as websocket:
        receive_until(websocket, "frame")
        values = {"values": {"ants.speed": 2.0}}
        client.patch(f"{API}/simulations/{simulation_id}/parameters", json=values)
        config = receive_until(websocket, "config")
        assert config["payload"]["ants"]["speed"] == 2.0


def test_event_notices_include_event(client, simulation_id):
    with stream(client, simulation_id) as websocket:
        receive_until(websocket, "frame")
        client.post(f"{API}/simulations/{simulation_id}/events", json={"type": "drought"})
        notice = receive_until(websocket, "event")
        assert notice["payload"]["kind"] == "event_scheduled"
        assert notice["payload"]["event"]["type"] == "drought"


def test_full_queue_drops_frames_but_keeps_control_messages():
    from hormiguero.engine.simulation import Subscriber

    subscriber = Subscriber()
    subscriber.queue = __import__("asyncio").Queue(maxsize=2)
    subscriber.send({"type": "frame"})
    subscriber.send({"type": "frame"})
    subscriber.send({"type": "frame"})
    subscriber.send({"type": "status"})
    kept = [subscriber.queue.get_nowait() for _ in range(2)]
    assert [message["seq"] for message in kept] == [2, 4]
    assert kept[1]["type"] == "status"


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
