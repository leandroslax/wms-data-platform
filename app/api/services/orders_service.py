from app.api.services.data_access import DataAccessService

class OrdersService:
    def __init__(self) -> None:
        self.data_access = DataAccessService()

    def get_summary(self) -> dict:
        return self.data_access.fetch_orders_summary()
