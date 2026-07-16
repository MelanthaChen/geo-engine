import hashlib
import json
import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.account import Account
from app.models.platform_question import PlatformQuestion
from app.services.account_service import seed_demo_accounts
from app.services.history.faq_history_service import create_faq_set
from app.services.platform_retrievers import (
    RetrievedPlatformQuestion,
    get_platform_retriever,
)
from app.services.platform_retrievers.utils import normalize_text
from app.services.publishing_service import select_publish_account


logger = logging.getLogger(__name__)


def log_platform_faq_debug(event: str, **fields):
    logger.info(
        "[PLATFORM FAQ DEBUG] %s",
        json.dumps({"event": event, **fields}, default=str),
    )


def discover_platform_faqs(
    db: Session,
    category: str,
    website_url: str | None,
    property_id: int | None = None,
    publish_platform: str = "reddit",
    account_id: int | None = None,
):
    log_platform_faq_debug(
        "discover_platform_faqs.received",
        category=category,
        website_url=website_url,
        property_id=property_id,
        publish_platform=publish_platform,
        account_id=account_id,
    )

    try:
        selected_account = select_discovery_account(
            db=db,
            account_id=account_id,
            publish_platform=publish_platform,
            property_id=property_id,
        )
        log_platform_faq_debug(
            "discover_platform_faqs.selected_account",
            publish_platform=publish_platform,
            account_id=getattr(selected_account, "id", None),
            account_handle=getattr(selected_account, "handle", None),
            session_path=getattr(selected_account, "session_path", None),
        )

        retrieved_questions = collect_external_platform_questions(
            db=db,
            category=category,
            property_id=property_id,
            publish_platform=publish_platform,
            account=selected_account,
        )
        log_platform_faq_debug(
            "discover_platform_faqs.retrieved",
            publish_platform=publish_platform,
            retrieved_question_count=len(retrieved_questions),
        )

        saved_questions = save_platform_questions(
            db=db,
            property_id=property_id,
            questions=retrieved_questions,
        )
    except Exception:
        logger.exception(
            "[PLATFORM FAQ DEBUG] discover_platform_faqs.exception "
            "publish_platform=%s category=%s",
            publish_platform,
            category,
        )
        raise

    faq_set = create_faq_set(
        db=db,
        property_id=property_id,
        category=category,
        faq_source="PLATFORM",
        questions=[question.title for question in saved_questions[:20]],
        website_url=website_url,
    )
    setattr(faq_set, "_platform_questions", saved_questions)

    return faq_set


def discover_platform_posts(
    db: Session,
    category: str,
    property_id: int | None = None,
    publish_platform: str = "xiaohongshu",
    account_id: int | None = None,
) -> list[PlatformQuestion]:
    log_platform_faq_debug(
        "discover_platform_posts.received",
        category=category,
        property_id=property_id,
        publish_platform=publish_platform,
        account_id=account_id,
    )

    selected_account = select_discovery_account(
        db=db,
        account_id=account_id,
        publish_platform=publish_platform,
        property_id=property_id,
    )

    retrieved_posts = collect_external_platform_questions(
        db=db,
        category=category,
        property_id=property_id,
        publish_platform=publish_platform,
        account=selected_account,
    )

    saved_posts = save_platform_questions(
        db=db,
        property_id=property_id,
        questions=retrieved_posts,
    )

    log_platform_faq_debug(
        "discover_platform_posts.completed",
        category=category,
        property_id=property_id,
        publish_platform=publish_platform,
        saved_post_count=len(saved_posts),
    )

    return saved_posts


def collect_external_platform_questions(
    db: Session,
    category: str,
    property_id: int | None = None,
    publish_platform: str = "reddit",
    account: Account | None = None,
) -> list[RetrievedPlatformQuestion]:
    retriever = get_platform_retriever(publish_platform)
    limit = retrieval_limit_for_platform(publish_platform)

    log_platform_faq_debug(
        "collect_external_platform_questions.start_retriever",
        publish_platform=publish_platform,
        retriever_class=type(retriever).__name__,
        category=category,
        limit=limit,
        property_id=property_id,
        account_id=getattr(account, "id", None),
    )

    try:
        questions = retriever.search(
            query=category,
            limit=limit,
            db=db,
            property_id=property_id,
            account=account,
        )
    except Exception:
        logger.exception(
            "[PLATFORM FAQ DEBUG] collect_external_platform_questions.exception "
            "publish_platform=%s retriever_class=%s category=%s",
            publish_platform,
            type(retriever).__name__,
            category,
        )
        raise

    log_platform_faq_debug(
        "collect_external_platform_questions.completed",
        publish_platform=publish_platform,
        retriever_class=type(retriever).__name__,
        retrieved_question_count=len(questions),
    )
    return questions


def select_discovery_account(
    db: Session,
    account_id: int | None,
    publish_platform: str,
    property_id: int | None,
):
    normalized_platform = (publish_platform or "reddit").strip().lower()

    if normalized_platform != "xiaohongshu":
        return None

    account = select_publish_account(
        db=db,
        account_id=account_id,
        publish_platform=normalized_platform,
        property_id=property_id,
    )

    if not account and property_id is not None:
        seed_demo_accounts(db, property_id=property_id)
        account = select_publish_account(
            db=db,
            account_id=account_id,
            publish_platform=normalized_platform,
            property_id=property_id,
        )

    return account


def retrieval_limit_for_platform(platform: str | None):
    normalized_platform = (platform or "reddit").strip().lower()

    if normalized_platform == "xiaohongshu":
        return settings.XIAOHONGSHU_RETRIEVAL_LIMIT

    return 20


def save_platform_questions(
    db: Session,
    property_id: int | None,
    questions: list[RetrievedPlatformQuestion],
) -> list[PlatformQuestion]:
    log_platform_faq_debug(
        "save_platform_questions.received",
        property_id=property_id,
        retrieved_question_count=len(questions),
    )
    saved_questions: list[PlatformQuestion] = []
    seen_hashes: set[str] = set()

    for question in questions:
        normalized_title = normalize_text(question.title)
        content_hash = build_content_hash(
            property_id=property_id,
            title=normalized_title,
            body=question.body,
        )

        if content_hash in seen_hashes:
            continue

        seen_hashes.add(content_hash)

        existing = (
            db.query(PlatformQuestion)
            .filter(
                PlatformQuestion.property_id == property_id,
                PlatformQuestion.content_hash == content_hash,
            )
            .first()
        )

        if existing:
            saved_questions.append(existing)
            continue

        platform_question = PlatformQuestion(
            property_id=property_id,
            platform=question.platform,
            title=question.title,
            body=question.body,
            url=question.url,
            author=question.author,
            hashtags=json.dumps(question.hashtags or []),
            score=question.score,
            engagement_metrics=json.dumps(question.engagement_metrics or {}),
            retrieval_method=question.retrieval_method,
            raw_metadata=json.dumps(question.raw_metadata or {}),
            created_at=question.created_at,
            content_hash=content_hash,
        )
        db.add(platform_question)
        saved_questions.append(platform_question)

    db.commit()

    for question in saved_questions:
        db.refresh(question)

    log_platform_faq_debug(
        "save_platform_questions.completed",
        property_id=property_id,
        saved_question_count=len(saved_questions),
    )
    return saved_questions


def serialize_platform_question(question: PlatformQuestion):
    return {
        "id": question.id,
        "property_id": question.property_id,
        "platform": question.platform,
        "title": question.title,
        "body": question.body,
        "url": question.url,
        "author": question.author,
        "hashtags": parse_json_field(question.hashtags, []),
        "score": question.score,
        "engagement_metrics": parse_json_field(question.engagement_metrics, {}),
        "retrieval_method": question.retrieval_method,
        "raw_metadata": parse_json_field(question.raw_metadata, {}),
        "created_at": question.created_at,
        "discovered_at": question.discovered_at,
        "content_hash": question.content_hash,
    }


def platform_question_to_retrieved_question(
    row: PlatformQuestion,
    retrieval_method: str,
):
    return RetrievedPlatformQuestion(
        platform=row.platform,
        title=row.title,
        body=row.body,
        url=row.url,
        author=row.author,
        hashtags=parse_json_field(row.hashtags, []),
        score=row.score,
        engagement_metrics=parse_json_field(row.engagement_metrics, {}),
        created_at=row.created_at,
        retrieval_method=retrieval_method,
        raw_metadata=parse_json_field(row.raw_metadata, {}),
    )


def build_content_hash(
    property_id: int | None,
    title: str,
    body: str | None,
):
    normalized_body = normalize_text(body or "")
    hash_input = f"{property_id or 'global'}::{title}::{normalized_body}"

    return hashlib.sha256(hash_input.encode("utf-8")).hexdigest()


def parse_json_field(value: str | None, fallback):
    if not value:
        return fallback

    try:
        return json.loads(value)
    except Exception:
        return fallback
