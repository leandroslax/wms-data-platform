from fastapi.testclient import TestClient

from app.api.main import app

client = TestClient(app)

def test_orders_summary_endpoint() -> None:
    response = client.get("/orders/summary")

    assert response.status_code == 200
    assert response.json() == {
        "total_orders": 0,
        "total_units": 0,
        "total_revenue": 0.0,
    }
