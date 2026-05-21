from pydantic import BaseModel

from typing import List


class ContentGenerationRequest(BaseModel):
    query: str
    persona: str
    content_type: str


class ContentGenerationResponse(BaseModel):
    title: str
    summary: str
    content: str
    seo_keywords: List[str]