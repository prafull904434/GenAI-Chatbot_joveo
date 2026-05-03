from pydantic import BaseModel, Field
from typing import List, Dict


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=3, le=10)
    history: List[Dict[str, str]] = Field(default_factory=list)


class Source(BaseModel):
    url: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]