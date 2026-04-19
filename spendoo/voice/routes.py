from fastapi import APIRouter, UploadFile, HTTPException
from spendoo.core.services import ServiceContainer
import os
from spendoo.core.config import settings

router = APIRouter(prefix="/voice", tags=["Voice"])

voice_service = ServiceContainer.get_voice_service()
categorization_service = ServiceContainer.get_categorization_service()

@router.post("/process")
async def process_voice(file: UploadFile):

    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in settings.VOICE_ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Unsupported audio format")

    audio_bytes = await file.read()

    if len(audio_bytes) > settings.VOICE_MAX_SIZE:
        raise HTTPException(400, "Audio file too large (max 25MB)")

    text = voice_service.transcribe(audio_bytes, file.filename)

    result = categorization_service.extract(text)

    return result