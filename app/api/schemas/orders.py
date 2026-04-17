from pydantic import BaseModel

class OrdersSummaryResponse(BaseModel):
    total_orders: int
    total_units: int
    total_revenue: float
