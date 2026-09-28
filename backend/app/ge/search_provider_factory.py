"""Configuration-driven live search provider selection."""

from app.core.config import settings
from app.ge.brave_search_provider import BraveSearchProvider
from app.ge.exa_search_provider import ExaSearchProvider
from app.ge.google_search_provider import GoogleSearchProvider
from app.ge.search_provider import SearchProvider


def build_search_provider() -> SearchProvider:
    if settings.SEARCH_PROVIDER == "exa":
        return ExaSearchProvider()
    if settings.SEARCH_PROVIDER == "brave":
        return BraveSearchProvider()
    if settings.SEARCH_PROVIDER == "google":
        return GoogleSearchProvider(require_api_credentials=True)
    raise ValueError(f"Unsupported SEARCH_PROVIDER: {settings.SEARCH_PROVIDER}")


def configured_search_provider_name() -> str:
    return {
        "exa": "Exa",
        "brave": "Brave Search",
        "google": "Google Custom Search",
    }[settings.SEARCH_PROVIDER]
