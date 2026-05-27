from pydantic import BaseModel


class ContentGenerationRequest(BaseModel):

    query: str

    persona: str

    content_type: str

    mode: str