import base64

from conftest import API


def control(client, simulation_id, **body):
    return client.post(f"{API}/simulations/{simulation_id}/control", json=body)


def test_create_and_get(client, simulation_id):
    info = client.get(f"{API}/simulations/{simulation_id}").json()
    assert info["status"] == "created"
    assert info["tick"] == 0
    assert info["seed"] == 7
    assert len(client.get(f"{API}/simulations").json()) == 1


def test_create_from_scenario_schedules_events(client):
    simulation_id = client.post(f"{API}/simulations", json={"scenario_id": "drought"}).json()["id"]
    events = client.get(f"{API}/simulations/{simulation_id}/events").json()
    assert events[0]["type"] == "drought"
    assert events[0]["status"] == "scheduled"


def test_create_rejects_scenario_and_config_together(client):
    response = client.post(f"{API}/simulations", json={"scenario_id": "baseline", "config": {}})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_rejects_unknown_scenario(client):
    response = client.post(f"{API}/simulations", json={"scenario_id": "mars"})
    assert response.json()["error"]["code"] == "unknown_scenario"


def test_create_rejects_nest_outside_world(client):
    config = {"world": {"width": 50, "height": 50, "nest_x": 100, "nest_y": 100}}
    assert client.post(f"{API}/simulations", json={"config": config}).status_code == 422


def test_missing_simulation_returns_404(client):
    response = client.get(f"{API}/simulations/sim_missing")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "simulation_not_found"


def test_step_advances_ticks_and_pauses(client, simulation_id):
    info = control(client, simulation_id, action="step", steps=5).json()
    assert info["tick"] == 5
    assert info["status"] == "paused"


def test_invalid_transitions_return_409(client, simulation_id):
    assert control(client, simulation_id, action="pause").status_code == 409
    assert control(client, simulation_id, action="start", speed=60).json()["status"] == "running"
    response = control(client, simulation_id, action="step")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_transition"
    assert control(client, simulation_id, action="pause").json()["status"] == "paused"


def test_reset_returns_to_tick_zero(client, simulation_id):
    control(client, simulation_id, action="step", steps=3)
    info = control(client, simulation_id, action="reset").json()
    assert info["tick"] == 0
    assert info["status"] == "created"


def test_set_speed_while_running(client, simulation_id):
    control(client, simulation_id, action="start", speed=10)
    info = control(client, simulation_id, action="set_speed", speed=90).json()
    assert info["speed"] == 90
    assert info["status"] == "running"
    control(client, simulation_id, action="pause")


def test_rejected_transition_keeps_speed(client, simulation_id):
    assert control(client, simulation_id, action="pause", speed=99).status_code == 409
    assert client.get(f"{API}/simulations/{simulation_id}").json()["speed"] == 30


def test_control_option_validation(client, simulation_id):
    assert control(client, simulation_id, action="set_speed").status_code == 422
    assert control(client, simulation_id, action="start", seed=3).status_code == 422


def test_reset_with_new_seed_and_kept_obstacles(client, simulation_id):
    client.post(f"{API}/simulations/{simulation_id}/world/obstacles", json={"cells": [[10, 10]], "radius": 2})
    info = control(client, simulation_id, action="reset", seed=99, keep_obstacles=True).json()
    assert info["seed"] == 99
    field = client.get(f"{API}/simulations/{simulation_id}/fields/obstacles").json()
    assert any(base64.b64decode(field["data"]))
    control(client, simulation_id, action="reset")
    field = client.get(f"{API}/simulations/{simulation_id}/fields/obstacles").json()
    assert not any(base64.b64decode(field["data"]))


def test_finished_simulation_can_be_extended(client, simulation_id):
    path = f"{API}/simulations/{simulation_id}/parameters"
    client.patch(path, json={"values": {"run.max_ticks": 100}})
    control(client, simulation_id, action="step", steps=100)
    assert control(client, simulation_id, action="step").json()["error"]["code"] == "simulation_finished"
    client.patch(path, json={"values": {"run.max_ticks": 120}})
    info = control(client, simulation_id, action="step", steps=50).json()
    assert info["tick"] == 120
    assert info["status"] == "finished"


def test_simulation_finishes_at_max_ticks(client, simulation_id):
    client.patch(f"{API}/simulations/{simulation_id}/parameters", json={"values": {"run.max_ticks": 100}})
    info = control(client, simulation_id, action="step", steps=150).json()
    assert info["status"] == "finished"
    assert info["finish_reason"] == "max_ticks"
    assert control(client, simulation_id, action="start").status_code == 409


def test_live_parameter_update(client, simulation_id):
    control(client, simulation_id, action="step")
    path = f"{API}/simulations/{simulation_id}/parameters"
    config = client.patch(path, json={"values": {"pheromones.food_evaporation": 0.5}}).json()
    assert config["pheromones"]["food_evaporation"] == 0.5


def test_parameter_update_errors(client, simulation_id):
    path = f"{API}/simulations/{simulation_id}/parameters"
    assert client.patch(path, json={"values": {"ants.wings": 1}}).json()["error"]["code"] == "unknown_parameter"
    assert client.patch(path, json={"values": {"ants.speed": 99}}).json()["error"]["code"] == "invalid_parameter"
    control(client, simulation_id, action="step")
    response = client.patch(path, json={"values": {"world.width": 100}})
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "parameter_requires_reset"


def test_non_live_parameter_rebuilds_world_before_start(client, simulation_id):
    path = f"{API}/simulations/{simulation_id}/parameters"
    client.patch(path, json={"values": {"world.width": 120, "world.nest_x": 60}})
    assert client.get(f"{API}/simulations/{simulation_id}").json()["world_width"] == 120


def test_state_snapshot(client, simulation_id):
    state = client.get(f"{API}/simulations/{simulation_id}/state").json()
    ants = state["frame"]["ants"]
    assert len(ants["ids"]) == len(ants["x"]) == len(ants["state"]) == len(ants["age"]) == 100
    assert state["world"]["nest"] == {"x": 100, "y": 100, "radius": 5}
    assert state["frame"]["nest"]["stocks"]["workers"] == 100


def test_field_encoding_matches_dimensions(client, simulation_id):
    field = client.get(f"{API}/simulations/{simulation_id}/fields/food", params={"downsample": 4}).json()
    assert field["width"] == 50 and field["height"] == 50
    assert len(base64.b64decode(field["data"])) == 50 * 50
    assert field["scale"] > 0


def test_history_filters(client, simulation_id):
    control(client, simulation_id, action="step", steps=10)
    params = {"keys": ["stocks.food", "metrics.alive_ants"], "from_tick": 2, "every": 2}
    history = client.get(f"{API}/simulations/{simulation_id}/history", params=params).json()
    assert history["ticks"] == [2, 4, 6, 8, 10]
    assert set(history["series"]) == {"stocks.food", "metrics.alive_ants"}
    assert len(history["series"]["stocks.food"]) == 5


def test_history_includes_deaths(client, simulation_id):
    params = {"keys": ["deaths.predator", "deaths.flood", "deaths.starvation", "deaths.old_age"]}
    history = client.get(f"{API}/simulations/{simulation_id}/history", params=params).json()
    assert history["resolution"] == 1
    assert history["series"]["deaths.predator"] == [0.0]


def test_history_compacts_instead_of_dropping_start():
    from hormiguero.engine.history import History
    from hormiguero.engine.mock_model import MockModel
    from hormiguero.schemas.config import SimulationConfig

    frame = MockModel(SimulationConfig(), seed=1).frame([])
    history = History(capacity=10)
    for tick in range(40):
        history.append(tick, frame)
    response = history.query(None)
    assert response.ticks[0] == 0
    assert response.resolution == 4
    assert response.ticks == list(range(0, 40, 4))


def test_history_rejects_unknown_key(client, simulation_id):
    response = client.get(f"{API}/simulations/{simulation_id}/history", params={"keys": ["stocks.gold"]})
    assert response.status_code == 422


def test_summary_and_export(client, simulation_id):
    control(client, simulation_id, action="step", steps=5)
    summary = client.get(f"{API}/simulations/{simulation_id}/metrics/summary").json()
    assert summary["ticks_elapsed"] == 5
    assert summary["colony_alive"] is True
    csv_response = client.get(f"{API}/simulations/{simulation_id}/export")
    assert csv_response.headers["content-type"].startswith("text/csv")
    lines = csv_response.text.strip().splitlines()
    assert lines[0].startswith("tick,stocks.food")
    assert len(lines) == 7
    json_export = client.get(f"{API}/simulations/{simulation_id}/export", params={"format": "json"}).json()
    assert json_export["ticks"] == [0, 1, 2, 3, 4, 5]


def test_delete_simulation(client, simulation_id):
    assert client.delete(f"{API}/simulations/{simulation_id}").status_code == 204
    assert client.get(f"{API}/simulations/{simulation_id}").status_code == 404
