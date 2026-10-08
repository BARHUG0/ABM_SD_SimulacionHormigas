import pytest
from fastapi.testclient import TestClient

from hormiguero.main import create_app

API = "/api/v1"


@pytest.fixture
def client():
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def simulation_id(client):
    response = client.post(f"{API}/simulations", json={"seed": 7})
    return response.json()["id"]
