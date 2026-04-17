from fastapi import APIRouter

from app.api.schemas.movements import MovementsSummaryResponse
from app.api.services.movements_service import MovementsService

router = APIRouter()
service = MovementsService()

@router.get("/summary", response_model=MovementsSummaryResponse)
def get_movements_summary() -> MovementsSummaryResponse:
    return MovementsSummaryResponse(**service.get_summary())
