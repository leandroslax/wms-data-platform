from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

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

# ── Frontend estático ──────────────────────────────────────────
_static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

    @app.get("/", include_in_schema=False)
    def frontend():
        return FileResponse(os.path.join(_static_dir, "index.html"))
