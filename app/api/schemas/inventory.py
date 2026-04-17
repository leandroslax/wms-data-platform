from pydantic import BaseModel

class InventorySnapshotResponse(BaseModel):
    total_skus: int
    total_on_hand_qty: int
    total_allocated_qty: int
    total_available_qty: int
