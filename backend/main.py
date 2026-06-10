from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from app.core.database import Base, engine
from app.core.schema_maintenance import ensure_additive_columns
from app.models import *

from app.api.v1.query_routes import router as query_router
from app.api.v1.content_routes import router as content_router
from app.api.v1.citation_routes import router as citation_router
from app.api.v1.publishing_routes import (
    router as publishing_router
)
from app.api.v1.citation_test_routes import (
    router as citation_test_router
)
from app.api.v1.campaign_routes import (
    router as campaign_router
)
from app.api.v1.campaign_runner_routes import (
    router as campaign_runner_router
)
from app.api.v1.optimization_routes import (
    router as optimization_router
)
from app.api.v1.account_routes import (
    router as account_router
)

Base.metadata.create_all(bind=engine)
ensure_additive_columns(engine)

app = FastAPI(
    title="GEO Engine API",
    version="1.0.0"
)

#
# Allowed frontend origins
#

origins = [
    "http://localhost:5173",
    "https://geo-engine-phi.vercel.app",
]

#
# Enable CORS
#

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#
# Root route
#

@app.get("/")
async def root():

    return {
        "message": "GEO Engine API running"
    }

#
# Health check
#

@app.get("/health")
async def health_check():

    return {
        "status": "healthy"
    }

#
# Register routers
#

app.include_router(
    query_router,
    prefix="/api/v1/queries",
    tags=["Query Engine"]
)

app.include_router(content_router)
app.include_router(citation_router)
app.include_router(publishing_router)
app.include_router(citation_test_router)
app.include_router(campaign_router)
app.include_router(campaign_runner_router)
app.include_router(optimization_router)
app.include_router(account_router)
