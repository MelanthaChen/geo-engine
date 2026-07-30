from pydantic import BaseModel

from typing import List


class QueryGenerationRequest(BaseModel):

    category: str

    niche: str

    provider: str | None = "chatgpt"


class QueryGenerationResponse(BaseModel):

    queries: List[str]
