from fastapi import APIRouter

from app.api.schemas.orders import OrdersSummaryResponse
from app.api.services.orders_service import OrdersService

router = APIRouter()
service = OrdersService()

@router.get("/summary", response_model=OrdersSummaryResponse)
def get_orders_summary() -> OrdersSummaryResponse:
    return OrdersSummaryResponse(**service.get_summary())
