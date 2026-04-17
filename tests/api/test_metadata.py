from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)

def test_metadata_endpoint() -> None:
    response = client.get("/metadata")

    assert response.status_code == 200

    payload = response.json()
    assert payload["project"] == "wms-data-platform"
    assert payload["environment"] == "dev"
    assert payload["mvp_entities"] == ["orders", "inventory", "movements"]
