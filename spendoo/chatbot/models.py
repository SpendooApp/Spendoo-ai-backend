from pydantic import BaseModel
from typing import Optional
import uuid

class ChatRequest(BaseModel):
    userId: uuid.UUID
    message: str
    chatSummary: Optional[str] = ""

class ChatResponse(BaseModel):
    response: str
    chatSummary: Optional[str] = ""

