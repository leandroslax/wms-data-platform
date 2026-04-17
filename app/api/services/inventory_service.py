from app.api.services.data_access import DataAccessService

class InventoryService:
    def __init__(self) -> None:
        self.data_access = DataAccessService()

    def get_snapshot(self) -> dict:
        return self.data_access.fetch_inventory_snapshot()
