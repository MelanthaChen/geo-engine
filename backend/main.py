from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.models import *
from app.services.property_service import seed_default_property

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
from app.api.v1.history_routes import (
    router as history_router
)
from app.api.v1.property_routes import (
    router as property_router
)
from app.api.v1.audit_routes import (
    router as audit_router
)
from app.api.v1.experiment_lab_routes import (
    router as experiment_lab_router
)
from app.api.v1.benchmark_routes import (
    router as benchmark_router
)
from app.api.v1.provider_routes import (
    router as provider_router
)
from app.predictor.router import router as predictor_router
from app.teacher_pipeline.router import router as teacher_pipeline_router

Base.metadata.create_all(bind=engine)

with SessionLocal() as db:
    seed_default_property(db)

app = FastAPI(
    title="GEO Engine API",
    version="1.0.0"
)

#
# Allowed frontend origins
#

origins = settings.frontend_origins

#
# Enable CORS
#

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


GEO_AI_RESUME_DEMO_HTML = """<!doctype html>
<html><head><title>Resume Gap Explanation Guide | GeoAIResume</title>
<meta name="description" content="How to address resume gaps with clarity, professionalism, and role-relevant evidence."></head>
<body><main><h1>Resume Gap Explanation Guide</h1>
<p>How to address resume gaps with clarity, professionalism, and role-relevant evidence.</p>
<p>Resume gaps can feel difficult to explain, but they do not have to dominate the application. The goal is to provide enough context without overexplaining personal details.</p>
<p>Candidates can address gaps through concise date formatting, summaries, recent projects, volunteer work, coursework, or contract experience when relevant. The resume should quickly return attention to current readiness. Career changers and caregivers may benefit from emphasizing refreshed skills and recent evidence. RRI improves when the document is complete and readable rather than evasive.</p>
<p>Explain gaps briefly when needed, then lead the reader back to role-relevant evidence. Clarity is better than avoidance.</p>
</main></body></html>"""


#
# Root route
#

@app.get("/")
async def root():
    return HTMLResponse(GEO_AI_RESUME_DEMO_HTML)

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
app.include_router(history_router)
app.include_router(property_router)
app.include_router(audit_router)
app.include_router(experiment_lab_router)
app.include_router(benchmark_router)
app.include_router(provider_router)
app.include_router(predictor_router)
app.include_router(teacher_pipeline_router)
