from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.models import *

from app.api.v1.query_routes import router as query_router
from app.api.v1.content_routes import router as content_router

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="GEO Engine API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


app.include_router(
    query_router,
    prefix="/api/v1/queries",
    tags=["Query Engine"]
)

app.include_router(content_router)