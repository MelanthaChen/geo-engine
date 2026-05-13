from fastapi import FastAPI

app = FastAPI(
    title="GEO Engine API",
    version="1.0.0",
)


@app.get("/")
async def root():
    return {
        "message": "GEO Engine API running"
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy"
    }