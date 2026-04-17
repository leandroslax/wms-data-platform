from fastapi import FastAPI

app = FastAPI(
    title="WMS Data Platform API",
    version="0.1.0",
    description="Operational and analytical API for the WMS Data Platform.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
