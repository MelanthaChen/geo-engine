from pydantic import BaseModel


class ContentGenerationRequest(BaseModel):

    query: str

    persona: str

    content_type: str

    target_url: str | None = None

    mode: str