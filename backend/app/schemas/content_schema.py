from pydantic import BaseModel


class ContentGenerationRequest(BaseModel):

    query: str

    persona: str

    content_type: str

    product_url: str | None = None

    target_url: str | None = None

    ai_faq: str | None = None

    platform_faq: str | None = None

    faq_source: str | None = None

    mode: str
