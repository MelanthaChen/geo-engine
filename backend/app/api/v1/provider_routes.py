from fastapi import APIRouter

from app.services.session_resolver import SessionResolver


router = APIRouter(
    prefix="/api/v1/providers",
    tags=["Provider Engine"],
)


@router.get("/status")
def get_provider_status():
    resolver = SessionResolver()
    perplexity_profile = resolver.canonical_profile_dir("perplexity")

    return {
        "providers": [
            {
                "id": "chatgpt",
                "name": "OpenAI",
                "status": "connected",
                "detail": "ChatGPT is available through the Provider Engine.",
            },
            {
                "id": "perplexity",
                "name": "Perplexity",
                "status": (
                    "connected"
                    if perplexity_profile.exists()
                    else "missing_session"
                ),
                "detail": (
                    "Perplexity Web profile is available."
                    if perplexity_profile.exists()
                    else (
                        "Run `python save_platform_state.py perplexity` "
                        "to initialize the browser profile."
                    )
                ),
                "profile_path": str(perplexity_profile),
            },
            {
                "id": "claude",
                "name": "Anthropic",
                "status": "coming_soon",
                "detail": "Claude support is planned in a future release.",
            },
            {
                "id": "gemini",
                "name": "Google AI",
                "status": "coming_soon",
                "detail": "Gemini support is planned in a future release.",
            },
        ]
    }
