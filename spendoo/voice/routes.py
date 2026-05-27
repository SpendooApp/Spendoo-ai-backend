import uuid

from fastapi import APIRouter, UploadFile, HTTPException, Depends
from sqlalchemy.orm import Session
from spendoo.core.database import get_db
from spendoo.core.services import ServiceContainer
from spendoo.categorization.service import CategorizationService
from spendoo.core.config import settings
import os


router = APIRouter(prefix="/voice", tags=["Voice"])

voice_service = ServiceContainer.get_voice_service()

@router.post("/process/{user_id}")
async def process_voice(file: UploadFile, user_id: uuid.UUID, db: Session = Depends(get_db)):

    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in settings.VOICE_ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Unsupported audio format")

    audio_bytes = await file.read()

    if len(audio_bytes) > settings.VOICE_MAX_SIZE:
        raise HTTPException(400, "Audio file too large (max 25MB)")

    text = voice_service.transcribe(audio_bytes, file.filename)

    categorization_service = CategorizationService(db)

    result = categorization_service.extract(text, user_id)

    return result