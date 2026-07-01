from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from spendoo.core.database import get_db
from spendoo.chatbot.models import ChatRequest, ChatResponse
from spendoo.chatbot.service import ChatbotService

router = APIRouter(prefix="/chatbot", tags=["chatbot"])

@router.post("/", response_model=ChatResponse)
def process_chat(request: ChatRequest, db: Session = Depends(get_db)):
    service = ChatbotService(db)
    return service.process_chat(request)
