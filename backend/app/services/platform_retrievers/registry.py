from app.services.platform_retrievers.base import RetrievalError
from app.services.platform_retrievers.reddit import RedditRetriever
from app.services.platform_retrievers.xiaohongshu import XiaohongshuRetriever


RETRIEVAL_REGISTRY = {
    "reddit": RedditRetriever,
    "xiaohongshu": XiaohongshuRetriever,
}


def get_platform_retriever(platform: str | None):
    normalized_platform = (platform or "reddit").strip().lower()
    retriever_class = RETRIEVAL_REGISTRY.get(normalized_platform)

    if not retriever_class:
        raise RetrievalError(
            f"No retrieval backend is registered for platform "
            f"{normalized_platform!r}."
        )

    return retriever_class()
