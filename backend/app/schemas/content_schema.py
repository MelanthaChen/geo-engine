from pydantic import BaseModel


class ContentGenerationRequest(BaseModel):

    query: str

    property_id: int | None = None

    persona: str

    content_type: str

    product_url: str | None = None

    target_url: str | None = None

    ai_faq: str | None = None

    platform_faq: str | None = None

    faq_source: str | None = None

    source_faq_set_id: int | None = None

    angle: str | None = None

    perspective: str | None = None

    archetype: str | None = None

    internet_style: str | None = None

    mode: str
