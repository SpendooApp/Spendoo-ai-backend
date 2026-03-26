from fastapi import APIRouter, UploadFile, HTTPException
from spendoo.voice.service import VoiceService
from spendoo.categorization.service import CategorizationService
import os

router = APIRouter(prefix="/voice", tags=["Voice"])

voice_service = VoiceService()
categorization_service = CategorizationService()

ALLOWED_EXTENSIONS = {".wav", ".mp3", ".ogg", ".m4a", ".flac", ".webm"}

MAX_SIZE = 25 * 1024 * 1024


@router.post("/process")
async def process_voice(file: UploadFile):


    ext = os.path.splitext(file.filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, "Unsupported audio format")

    audio_bytes = await file.read()

    if len(audio_bytes) > MAX_SIZE:
        raise HTTPException(400, "Audio file too large (max 25MB)")

    text = voice_service.transcribe(audio_bytes, file.filename)

    result = categorization_service.extract(text)

    return result