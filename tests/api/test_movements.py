from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)

def test_movements_summary_endpoint() -> None:
    response = client.get("/movements/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total_movements": 0,
        "total_units_moved": 0,
    }
