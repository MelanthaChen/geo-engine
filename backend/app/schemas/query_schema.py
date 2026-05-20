from pydantic import BaseModel

from typing import List


class QueryGenerationRequest(BaseModel):

    category: str

    niche: str


class QueryGenerationResponse(BaseModel):

    queries: List[str]