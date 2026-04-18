from fastapi import FastAPI

from app.api.routes import chat, health, inventory, metadata, movements, orders

app = FastAPI(
    title="WMS Data Platform API",
    version="0.1.0",
    description="Analytical API for the WMS Data Platform MVP.",
)

app.include_router(health.router, tags=["health"])
app.include_router(metadata.router, prefix="/metadata", tags=["metadata"])
app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
app.include_router(movements.router, prefix="/movements", tags=["movements"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
