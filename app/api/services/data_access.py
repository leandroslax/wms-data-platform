from typing import Any

class DataAccessService:
    """
    Temporary analytical access layer.

    This service currently returns mocked responses for the MVP while the
    local analytical serving layer is not connected yet. The public methods are
    already shaped to match the future PostgreSQL-backed contract.
    """

    def fetch_orders_summary(self) -> dict[str, Any]:
        return {
            "total_orders": 0,
            "total_units": 0,
            "total_revenue": 0.0,
        }

    def fetch_inventory_snapshot(self) -> dict[str, Any]:
        return {
            "total_skus": 0,
            "total_on_hand_qty": 0,
            "total_allocated_qty": 0,
            "total_available_qty": 0,
        }

    def fetch_movements_summary(self) -> dict[str, Any]:
        return {
            "total_movements": 0,
            "total_units_moved": 0,
        }
