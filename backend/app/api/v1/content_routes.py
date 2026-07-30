from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
)

import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.services.export_service import (
    generate_html_export
)

from app.models.content import Content
from app.models.faq_set import FaqSet
from app.models.publishing_job import PublishingJob
from app.services.property_service import get_property

from app.core.deps import get_db

from app.schemas.content_schema import (
    ContentGenerationRequest,
)

from app.services.content_service import (
    generate_content,
    fetch_all_contents,
    generate_faqs,
    normalize_publish_platform,
)
from app.services.retrieval_task_service import (
    claim_next_retrieval_task,
    complete_retrieval_task,
    create_retrieval_task,
    fail_retrieval_task,
    get_retrieval_task,
    list_task_platform_questions,
    serialize_retrieval_task,
)
from app.services.platform_retrievers import RetrievedPlatformQuestion
from app.repositories.history_repository import (
    get_recent_history_events
)
from app.utils.title_extractor import (
    extract_article_title
)

router = APIRouter(
    prefix="/api/v1/content",
    tags=["Content Engine"]
)

logger = logging.getLogger(__name__)


class RetrievedQuestionPayload(BaseModel):
    platform: str
    title: str
    body: str | None = None
    url: str | None = None
    author: str | None = None
    hashtags: list[str] | None = None
    score: int | None = None
    engagement_metrics: dict | None = None
    created_at: str | None = None
    retrieval_method: str | None = None
    raw_metadata: dict | None = None


class CompleteRetrievalTaskRequest(BaseModel):
    questions: list[RetrievedQuestionPayload]


class FailRetrievalTaskRequest(BaseModel):
    error_message: str


def log_platform_faq_debug(event: str, **fields):
    logger.info(
        "[PLATFORM FAQ DEBUG] %s",
        json.dumps({"event": event, **fields}, default=str),
    )


def content_title(content: Content):
    if content.reddit_title:
        return content.reddit_title

    return extract_article_title(
        generated_content=content.body,
        fallback=content.title
    )


def content_evidence(content: Content):
    if not content.evidence_json:
        return None

    try:
        return json.loads(content.evidence_json)
    except Exception:
        return None


def latest_publish_task(
    db: Session,
    content_id: int,
):
    return (
        db.query(PublishingJob)
        .filter(PublishingJob.content_id == content_id)
        .order_by(PublishingJob.created_at.desc())
        .first()
    )


def retrieved_question_from_payload(
    payload: RetrievedQuestionPayload,
) -> RetrievedPlatformQuestion:
    created_at = None

    if payload.created_at:
        try:
            created_at = datetime.fromisoformat(
                payload.created_at.replace("Z", "+00:00")
            )
        except ValueError:
            created_at = None

    return RetrievedPlatformQuestion(
        platform=payload.platform,
        title=payload.title,
        body=payload.body,
        url=payload.url,
        author=payload.author,
        hashtags=payload.hashtags,
        score=payload.score,
        engagement_metrics=payload.engagement_metrics,
        created_at=created_at,
        retrieval_method=payload.retrieval_method,
        raw_metadata=payload.raw_metadata,
    )


def publish_metadata(
    db: Session,
    content: Content,
):
    task = latest_publish_task(
        db=db,
        content_id=content.id
    )

    return {
        "publish_task_id": task.id if task else None,
        "published_account": task.account.handle if task else None,
        "published_account_id": task.account_id if task else None,
        "published_platform": (
            task.account.platform
            if task
            else content.publish_provider
        ),
        "published_url": content.published_url,
    }


def empty_publish_metadata():
    return {
        "publish_task_id": None,
        "published_account": None,
        "published_account_id": None,
        "published_platform": None,
        "published_url": None,
    }


def history_item_type(event):
    if event.publishing_job_id:
        return "publish"

    if event.citation_test_run_id:
        return "citation_test"

    if event.website_audit_id or event.event_type == "audit_run":
        return "audit"

    return "event"


def history_item_id(event):
    if event.publishing_job_id:
        return event.publishing_job_id

    if event.citation_test_run_id:
        return event.citation_test_run_id

    if event.website_audit_id:
        return event.website_audit_id

    return event.id


def history_title(event):
    if event.publishing_job:
        return content_title(event.publishing_job.content)

    if event.citation_test_run:
        return f"Citation Test: {event.citation_test_run.prompt[:80]}"

    if event.website_audit:
        return event.summary or "Website Audit"

    if event.event_type == "audit_run":
        return event.summary or "Website Audit"

    if event.content:
        return content_title(event.content)

    return event.summary or "System event"


def history_body(event):
    if event.publishing_job:
        return event.publishing_job.logs or event.metadata_json

    if event.citation_test_run:
        return "\n\n".join(
            (
                f"{result.model}: {result.status}\n"
                f"Mentioned: {result.mentioned}\n"
                f"Rank: {result.rank or '-'}\n"
                f"{result.raw_response or result.error_message or ''}"
            )
            for result in event.citation_test_run.results
        )

    if event.website_audit:
        return (
            f"Overall GEO Score: {event.website_audit.overall_geo_score}\n"
            f"Brand Summary: {event.website_audit.brand_summary}\n"
            f"Pages Crawled: {len(event.website_audit.pages)}\n"
            f"Recommendations: {len(event.website_audit.recommendations)}"
        )

    if event.content:
        return event.content.body

    return event.metadata_json


@router.post("/generate")
def generate_content_route(
    request: ContentGenerationRequest,
    db: Session = Depends(get_db),
):
    target_url = None

    if request.property_id:
        property_record = get_property(db, request.property_id)

        if property_record:
            target_url = property_record.domain
    else:
        target_url = request.product_url or request.target_url

    result = generate_content(
        db=db,
        query=request.query,
        property_id=request.property_id,
        persona=request.persona,
        content_type=request.content_type,
        target_url=target_url,
        mode=request.mode,
        ai_faq=request.ai_faq,
        platform_faq=request.platform_faq,
        faq_source=request.faq_source,
        source_faq_set_id=request.source_faq_set_id,
        publish_platform=request.publish_platform,
        provider=request.provider,
        angle=request.angle,
        perspective=request.perspective,
        archetype=request.archetype,
        internet_style=request.internet_style,
    )

    return {
        "generated_content":
            result.body,

        "title":
            result.title,

        "reddit_title":
            result.reddit_title,

        "reddit_body":
            result.reddit_body,

        "strategy_type":
            result.strategy_type,

        "content_type":
            result.content_type,

        "provider":
            result.provider,

        "target_url":
            result.target_url,

        "evidence":
            content_evidence(result),

        "ai_faq":
            result.ai_faq,

        "platform_faq":
            result.platform_faq,

        "faq_source":
            result.faq_source,

        "angle":
            result.angle,

        "perspective":
            result.perspective,

        "archetype":
            result.archetype,

        "internet_style":
            result.internet_style,

        "generated_angles":
            result.generated_angles,

        "content_id":
            result.id,

        "property_id":
            result.property_id
    }


@router.get("/history")
def get_content_history(
    property_id: int | None = None,
    db: Session = Depends(get_db),
):

    events = get_recent_history_events(db, property_id=property_id)

    event_rows = [
        {
            "id": f"event-{event.id}",
            "history_item_type": history_item_type(event),
            "history_item_id": history_item_id(event),
            "event_id": event.id,
            "content_id": event.content_id,
            "property_id": event.property_id,
            "title": history_title(event),
            "body": history_body(event),
            "reddit_title": (
                event.content.reddit_title if event.content else None
            ),
            "reddit_body": (
                event.content.reddit_body if event.content else None
            ),
            "content_type": (
                event.content.content_type if event.content else None
            ),
            "provider": (
                event.content.provider if event.content else None
            ),
            "strategy_type": (
                event.content.strategy_type if event.content else None
            ),
            "target_persona": (
                event.content.target_persona if event.content else None
            ),
            "target_url": (
                event.content.target_url if event.content else None
            ),
            "evidence": (
                content_evidence(event.content) if event.content else None
            ),
            "ai_faq": (
                event.content.ai_faq if event.content else None
            ),
            "platform_faq": (
                event.content.platform_faq if event.content else None
            ),
            "faq_source": (
                event.content.faq_source if event.content else None
            ),
            "angle": (
                event.content.angle if event.content else None
            ),
            "perspective": (
                event.content.perspective if event.content else None
            ),
            "archetype": (
                event.content.archetype if event.content else None
            ),
            "internet_style": (
                event.content.internet_style if event.content else None
            ),
            "generated_angles": (
                event.content.generated_angles if event.content else None
            ),
            "generation_mode": (
                event.content.generation_mode
                if event.content
                else None
            ),
            "publish_status": (
                event.content.publish_status if event.content else None
            ),
            **(
                publish_metadata(db, event.content)
                if event.content
                else empty_publish_metadata()
            ),
            "preview_title": (
                event.content.preview_title if event.content else None
            ),
            "preview_subreddit": (
                event.content.preview_subreddit if event.content else None
            ),
            "preview_screenshot": (
                event.content.preview_screenshot if event.content else None
            ),
            "preview_url": (
                event.content.preview_url if event.content else None
            ),
            "preview_timestamp": (
                event.content.preview_timestamp if event.content else None
            ),
            "citation_count": (
                event.content.citation_count if event.content else 0
            ),
            "visibility_score": (
                event.content.visibility_score if event.content else 0
            ),
            "event_type": event.event_type,
            "event_summary": event.summary,
            "publishing_job_id": event.publishing_job_id,
            "citation_test_run_id": event.citation_test_run_id,
            "event_status": event.event_type,
            "created_at": event.created_at,
        }
        for event in events
    ]

    faq_query = db.query(FaqSet)

    if property_id is not None:
        faq_query = faq_query.filter(FaqSet.property_id == property_id)

    faq_rows = [
        {
            "id": f"faq-set-{faq_set.id}",
            "history_item_type": "faq",
            "history_item_id": faq_set.id,
            "content_id": None,
            "property_id": faq_set.property_id,
            "title": f"{faq_set.faq_source} FAQ Discovery: {faq_set.category}",
            "body": "\n".join(
                f"{faq.rank}. {faq.question}"
                for faq in sorted(
                    faq_set.faqs,
                    key=lambda item: item.rank
                )
            ),
            "reddit_title": None,
            "reddit_body": None,
            "content_type": faq_set.content_type,
            "provider": faq_set.provider,
            "strategy_type": faq_set.content_type,
            "target_persona": faq_set.category,
            "target_url": faq_set.website_url,
            "evidence": None,
            "ai_faq": None,
            "platform_faq": None,
            "faq_source": faq_set.faq_source,
            "angle": None,
            "perspective": None,
            "archetype": None,
            "internet_style": None,
            "generated_angles": None,
            "generation_mode": "faq_discovery",
            "publish_status": "discovered",
            **empty_publish_metadata(),
            "preview_title": None,
            "preview_subreddit": None,
            "preview_screenshot": None,
            "preview_url": None,
            "preview_timestamp": None,
            "citation_count": 0,
            "visibility_score": 0,
            "event_type": "faq_discovery",
            "event_summary": (
                f"{faq_set.faq_source} FAQ set discovered for "
                f"{faq_set.category}"
            ),
            "event_status": "discovered",
            "created_at": faq_set.created_at,
        }
        for faq_set in (
            faq_query.order_by(FaqSet.created_at.desc())
            .all()
        )
    ]

    history_rows = event_rows + faq_rows

    history_rows = sorted(
        history_rows,
        key=lambda item: item["created_at"],
        reverse=True
    )

    return {
        "history": history_rows
    }


@router.get("/retrieval-tasks/pending")
def get_pending_retrieval_task(
    platform: str = "xiaohongshu",
    db: Session = Depends(get_db),
):
    task = claim_next_retrieval_task(
        db=db,
        platform=normalize_publish_platform(platform),
    )

    if not task:
        return {
            "task": None
        }

    return {
        "task": serialize_retrieval_task(task)
    }


@router.get("/retrieval-tasks/{task_id}")
def get_retrieval_task_route(
    task_id: int,
    db: Session = Depends(get_db),
):
    task = get_retrieval_task(
        db=db,
        task_id=task_id,
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Retrieval task not found",
        )

    platform_questions = list_task_platform_questions(
        db=db,
        task=task,
    )

    return {
        "task": serialize_retrieval_task(
            task,
            platform_questions=platform_questions,
        )
    }


@router.post("/retrieval-tasks/{task_id}/complete")
def complete_retrieval_task_route(
    task_id: int,
    request: CompleteRetrievalTaskRequest,
    db: Session = Depends(get_db),
):
    task, saved_questions = complete_retrieval_task(
        db=db,
        task_id=task_id,
        questions=[
            retrieved_question_from_payload(question)
            for question in request.questions
        ],
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Retrieval task not found",
        )

    return {
        "task": serialize_retrieval_task(
            task,
            platform_questions=[
                {
                    "id": question.id,
                    "property_id": question.property_id,
                    "platform": question.platform,
                    "title": question.title,
                    "body": question.body,
                    "url": question.url,
                    "author": question.author,
                    "hashtags": json.loads(question.hashtags or "[]"),
                    "score": question.score,
                    "engagement_metrics": json.loads(
                        question.engagement_metrics or "{}"
                    ),
                    "retrieval_method": question.retrieval_method,
                    "raw_metadata": json.loads(question.raw_metadata or "{}"),
                    "created_at": question.created_at,
                    "discovered_at": question.discovered_at,
                    "content_hash": question.content_hash,
                }
                for question in saved_questions
            ],
        )
    }


@router.post("/retrieval-tasks/{task_id}/failed")
def fail_retrieval_task_route(
    task_id: int,
    request: FailRetrievalTaskRequest,
    db: Session = Depends(get_db),
):
    task = fail_retrieval_task(
        db=db,
        task_id=task_id,
        error_message=request.error_message,
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Retrieval task not found",
        )

    return {
        "task": serialize_retrieval_task(task)
    }


@router.get("/faqs/{target}")
def generate_faqs_route(
    target: str,
    mode: str,
    content_type: str = "comparison",
    publish_platform: str = "reddit",
    website_url: str | None = None,
    property_id: int | None = None,
    account_id: int | None = None,
    provider: str | None = "chatgpt",
    db: Session = Depends(get_db),
):
    log_platform_faq_debug(
        "generate_faqs_route.received",
        target=target,
        mode=mode,
        content_type=content_type,
        publish_platform=publish_platform,
        website_url=website_url,
        property_id=property_id,
        account_id=account_id,
        provider=provider,
    )

    if (
        (mode or "").strip().lower() == "platform"
        and normalize_publish_platform(publish_platform) == "xiaohongshu"
    ):
        retrieval_task = create_retrieval_task(
            db=db,
            category=target,
            platform="xiaohongshu",
            content_type=content_type,
            property_id=property_id,
            account_id=account_id,
            provider=provider,
        )
        log_platform_faq_debug(
            "generate_faqs_route.xiaohongshu_task_created",
            target=target,
            property_id=property_id,
            retrieval_task_id=retrieval_task.id,
        )

        return {
            "target": target,
            "mode": mode,
            "status": "retrieving",
            "retrieval_task_id": retrieval_task.id,
            "faqs": "",
            "faq_set": None,
            "faq_set_id": None,
            "platform_questions": [],
            "result_type": "platform_posts",
        }

    try:
        result = generate_faqs(
            target=target,
            mode=mode,
            db=db,
            content_type=content_type,
            publish_platform=publish_platform,
            website_url=website_url,
            property_id=property_id,
            account_id=account_id,
        )
    except Exception as error:
        logger.exception(
            "[PLATFORM FAQ DEBUG] generate_faqs_route.exception "
            "publish_platform=%s target=%s",
            publish_platform,
            target,
        )
        raise HTTPException(
            status_code=500,
            detail={
                "message": str(error),
                "error_type": type(error).__name__,
                "publish_platform": publish_platform,
                "target": target,
            },
        ) from error

    log_platform_faq_debug(
        "generate_faqs_route.success",
        publish_platform=publish_platform,
        faq_set_id=(
            result["faq_set"]["id"]
            if result.get("faq_set")
            else None
        ),
        platform_question_count=len(result.get("platform_questions", [])),
        result_type=result.get("result_type", "faq"),
    )

    return {
        "target": target,
        "mode": mode,
        "faqs": result["text"],
        "faq_set": result["faq_set"],
        "faq_set_id": (
            result["faq_set"]["id"]
            if result.get("faq_set")
            else None
        ),
        "platform_questions": result.get("platform_questions", []),
        "result_type": result.get("result_type", "faq"),
    }


@router.get(
    "/export/{content_id}",
    response_class=HTMLResponse
)
def export_content(
    content_id: int,
    db: Session = Depends(get_db),
):

    content = (
        db.query(Content)
        .filter(Content.id == content_id)
        .first()
    )

    if not content:

        return HTMLResponse(
            content="<h1>Content not found</h1>",
            status_code=404
        )

    html = generate_html_export(content)

    return HTMLResponse(content=html)

@router.get("/{content_id}")
def get_content_by_id(
    content_id: int,
    property_id: int | None = None,
    db: Session = Depends(get_db),
):

    query = db.query(Content).filter(Content.id == content_id)

    if property_id is not None:
        query = query.filter(Content.property_id == property_id)

    content = query.first()

    if not content:

        return {
            "error": "Content not found"
        }

    return {
        "id": content.id,
        "property_id": content.property_id,
        "title": content_title(content),
        "body": content.body,
        "reddit_title": content.reddit_title,
        "reddit_body": content.reddit_body,
        "content_type": content.content_type,
        "provider": content.provider,
        "strategy_type": content.strategy_type,
        "target_url": content.target_url,
        "evidence": content_evidence(content),
        "ai_faq": content.ai_faq,
        "platform_faq": content.platform_faq,
        "faq_source": content.faq_source,
        "angle": content.angle,
        "perspective": content.perspective,
        "archetype": content.archetype,
        "internet_style": content.internet_style,
        "generated_angles": content.generated_angles,
        "publish_status": content.publish_status,
        **publish_metadata(db, content),
        "preview_title": content.preview_title,
        "preview_subreddit": content.preview_subreddit,
        "preview_screenshot": content.preview_screenshot,
        "preview_url": content.preview_url,
        "preview_timestamp": content.preview_timestamp
    }
