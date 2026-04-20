"""Chat endpoint schemas."""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Natural language question about WMS operations.",
        examples=["Quais operadores tiveram queda de produtividade esta semana?"],
    )


class ChatResponse(BaseModel):
    answer: str = Field(..., description="Structured answer from the WMS agent crew.")
    question: str = Field(..., description="Original question echoed back.")
