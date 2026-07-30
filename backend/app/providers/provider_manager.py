from app.core.llm_provider import normalize_llm_provider
from app.providers.base_provider import Provider
from app.providers.chatgpt_provider import ChatGPTProvider
from app.providers.claude_provider import ClaudeProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.perplexity_provider import PerplexityProvider


class ProviderManager:
    _providers: dict[str, type[Provider]] = {
        "chatgpt": ChatGPTProvider,
        "claude": ClaudeProvider,
        "gemini": GeminiProvider,
        "perplexity": PerplexityProvider,
    }

    @classmethod
    def get_provider(cls, provider_name: str | None = None) -> Provider:
        normalized = normalize_llm_provider(provider_name)
        provider_class = cls._providers.get(normalized)

        if not provider_class:
            raise ValueError(f"Unsupported LLM provider '{provider_name}'.")

        return provider_class()
