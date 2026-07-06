import json
import logging

from app.services.platform_retrievers.base import RetrievalError
from app.services.platform_retrievers.reddit import RedditRetriever
from app.services.platform_retrievers.xiaohongshu import XiaohongshuRetriever


logger = logging.getLogger(__name__)


def log_platform_faq_debug(event: str, **fields):
    logger.info(
        "[PLATFORM FAQ DEBUG] %s",
        json.dumps({"event": event, **fields}, default=str),
    )


RETRIEVAL_REGISTRY = {
    "reddit": RedditRetriever,
    "xiaohongshu": XiaohongshuRetriever,
}


def get_platform_retriever(platform: str | None):
    normalized_platform = (platform or "reddit").strip().lower()
    retriever_class = RETRIEVAL_REGISTRY.get(normalized_platform)
    log_platform_faq_debug(
        "retrieval_registry.lookup",
        publish_platform=platform,
        normalized_platform=normalized_platform,
        found=bool(retriever_class),
        retriever_class=getattr(retriever_class, "__name__", None),
        registered_platforms=sorted(RETRIEVAL_REGISTRY.keys()),
    )

    if not retriever_class:
        logger.error(
            "[PLATFORM FAQ DEBUG] retrieval_registry.not_found "
            "publish_platform=%s normalized_platform=%s",
            platform,
            normalized_platform,
        )
        raise RetrievalError(
            f"No retrieval backend is registered for platform "
            f"{normalized_platform!r}."
        )

    retriever = retriever_class()
    log_platform_faq_debug(
        "retrieval_registry.created",
        normalized_platform=normalized_platform,
        retriever_class=type(retriever).__name__,
    )
    return retriever
