from conftest import API


def url(simulation_id, path):
    return f"{API}/simulations/{simulation_id}{path}"


def step(client, simulation_id, steps):
    client.post(url(simulation_id, "/control"), json={"action": "step", "steps": steps})


def test_paint_and_erase_obstacles(client, simulation_id):
    ack = client.post(url(simulation_id, "/world/obstacles"), json={"cells": [[10, 10], [11, 10]], "radius": 2}).json()
    assert ack["kind"] == "obstacles"
    assert ack["command_id"].startswith("cmd_")
    scale = client.get(url(simulation_id, "/fields/obstacles")).json()["scale"]
    assert scale == 1.0
    client.post(url(simulation_id, "/world/obstacles"), json={"cells": [[10, 10], [11, 10]], "radius": 2, "mode": "erase"})
    assert client.get(url(simulation_id, "/fields/obstacles")).json()["scale"] == 0.0


def test_obstacles_out_of_bounds(client, simulation_id):
    response = client.post(url(simulation_id, "/world/obstacles"), json={"cells": [[500, 10]]})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "out_of_bounds"


def test_place_food_increases_world_food(client, simulation_id):
    before = client.get(url(simulation_id, "/state")).json()["frame"]["metrics"]["food_in_world"]
    client.post(url(simulation_id, "/world/food"), json={"x": 20, "y": 20, "amount": 250})
    after = client.get(url(simulation_id, "/state")).json()["frame"]["metrics"]["food_in_world"]
    assert round(after - before) == 250


def test_predators_add_and_remove(client, simulation_id):
    created = client.post(url(simulation_id, "/predators"), json={"x": 30, "y": 30, "count": 3})
    assert created.status_code == 201
    ids = created.json()["ids"]
    assert len(ids) == 3
    assert client.delete(url(simulation_id, f"/predators/{ids[0]}")).status_code == 200
    response = client.delete(url(simulation_id, f"/predators/{ids[0]}"))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "predator_not_found"


def test_predator_limit(client, simulation_id):
    for _ in range(2):
        client.post(url(simulation_id, "/predators"), json={"x": 30, "y": 30, "count": 20})
    response = client.post(url(simulation_id, "/predators"), json={"x": 30, "y": 30, "count": 20})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "predator_limit"


def test_event_lifecycle(client, simulation_id):
    event = client.post(url(simulation_id, "/events"), json={"type": "flood", "duration": 3}).json()
    assert event["status"] == "scheduled"
    assert event["start_tick"] == 1 and event["end_tick"] == 4
    step(client, simulation_id, 1)
    assert client.get(url(simulation_id, f"/events/{event['id']}")).json()["status"] == "active"
    frame = client.get(url(simulation_id, "/state")).json()["frame"]
    assert frame["active_event_ids"] == [event["id"]]
    step(client, simulation_id, 3)
    assert client.get(url(simulation_id, f"/events/{event['id']}")).json()["status"] == "finished"
    assert client.delete(url(simulation_id, f"/events/{event['id']}")).status_code == 409


def test_predator_wave_adds_and_removes_predators(client, simulation_id):
    client.post(url(simulation_id, "/events"), json={"type": "predator_wave", "predator_count": 4, "duration": 2})
    step(client, simulation_id, 1)
    assert client.get(url(simulation_id, "/state")).json()["frame"]["metrics"]["predators"] == 6
    step(client, simulation_id, 2)
    assert client.get(url(simulation_id, "/state")).json()["frame"]["metrics"]["predators"] == 2


def test_cancel_active_event(client, simulation_id):
    event = client.post(url(simulation_id, "/events"), json={"type": "drought", "duration": 50}).json()
    step(client, simulation_id, 1)
    assert client.delete(url(simulation_id, f"/events/{event['id']}")).json()["status"] == "cancelled"


def test_event_validation(client, simulation_id):
    wave = client.post(url(simulation_id, "/events"), json={"type": "predator_wave"})
    assert wave.status_code == 422
    region = {"x": 190, "y": 0, "width": 50, "height": 10}
    outside = client.post(url(simulation_id, "/events"), json={"type": "flood", "region": region})
    assert outside.json()["error"]["code"] == "out_of_bounds"
    step(client, simulation_id, 5)
    past = client.post(url(simulation_id, "/events"), json={"type": "flood", "start_tick": 2})
    assert past.json()["error"]["code"] == "start_tick_in_past"
