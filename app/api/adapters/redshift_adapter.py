from typing import Any

class RedshiftAdapter:
    """
    Future Redshift adapter for analytical serving.

    This adapter is intentionally not connected yet. It defines the interface
    expected by the application once the Redshift serving layer is available.
    """

    def fetch_orders_summary(self) -> dict[str, Any]:
        raise NotImplementedError("Redshift adapter is not connected yet.")

    def fetch_inventory_snapshot(self) -> dict[str, Any]:
        raise NotImplementedError("Redshift adapter is not connected yet.")

    def fetch_movements_summary(self) -> dict[str, Any]:
        raise NotImplementedError("Redshift adapter is not connected yet.")
