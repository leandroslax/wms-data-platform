from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)

def test_inventory_snapshot_endpoint() -> None:
    response = client.get("/inventory/snapshot")

    assert response.status_code == 200
    assert response.json() == {
        "total_skus": 0,
        "total_on_hand_qty": 0,
        "total_allocated_qty": 0,
        "total_available_qty": 0,
    }
