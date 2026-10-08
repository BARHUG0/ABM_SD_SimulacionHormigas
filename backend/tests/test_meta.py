from conftest import API


def test_health(client):
    assert client.get(f"{API}/health").json()["status"] == "ok"


def test_parameter_schema_exposes_bounds_and_live_flag(client):
    specs = {spec["key"]: spec for spec in client.get(f"{API}/parameters/schema").json()}
    evaporation = specs["pheromones.food_evaporation"]
    assert evaporation["minimum"] == 0 and evaporation["maximum"] == 1
    assert evaporation["live_editable"] is True
    assert specs["world.width"]["live_editable"] is False
    assert specs["ants.initial_workers"]["type"] == "int"


def test_scenarios_listed(client):
    ids = {scenario["id"] for scenario in client.get(f"{API}/scenarios").json()}
    assert {"baseline", "drought", "flood", "predator_invasion"} <= ids


def test_openapi_includes_websocket_messages(client):
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert {"ServerMessage", "ClientMessage", "FrameMessage", "SubscribeMessage"} <= set(schemas)


def test_unknown_route_uses_error_format(client):
    response = client.get(f"{API}/nope")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"
