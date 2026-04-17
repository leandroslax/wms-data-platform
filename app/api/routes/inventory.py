from fastapi import APIRouter

from app.api.schemas.inventory import InventorySnapshotResponse
from app.api.services.inventory_service import InventoryService

router = APIRouter()
service = InventoryService()

@router.get("/snapshot", response_model=InventorySnapshotResponse)
def get_inventory_snapshot() -> InventorySnapshotResponse:
    return InventorySnapshotResponse(**service.get_snapshot())
