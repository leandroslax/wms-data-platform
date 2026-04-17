from pydantic import BaseModel

class MovementsSummaryResponse(BaseModel):
    total_movements: int
    total_units_moved: int
