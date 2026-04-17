from fastapi import APIRouter

router = APIRouter()

@router.get("")
def metadata() -> dict:
    return {
        "project": "wms-data-platform",
        "environment": "dev",
        "mvp_entities": ["orders", "inventory", "movements"],
        "data_layers": ["bronze", "silver", "gold"],
        "serving_targets": ["api", "dashboards", "agents"],
    }
