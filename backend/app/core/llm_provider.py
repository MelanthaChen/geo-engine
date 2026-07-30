DEFAULT_LLM_PROVIDER = "chatgpt"
SUPPORTED_LLM_PROVIDERS = {
    DEFAULT_LLM_PROVIDER,
    "claude",
    "gemini",
    "perplexity",
}


def normalize_llm_provider(provider: str | None = None) -> str:
    normalized = (provider or DEFAULT_LLM_PROVIDER).strip().lower()

    if normalized not in SUPPORTED_LLM_PROVIDERS:
        raise ValueError(
            f"Unsupported LLM provider '{provider}'. "
            f"Supported providers: {', '.join(sorted(SUPPORTED_LLM_PROVIDERS))}."
        )

    return normalized
