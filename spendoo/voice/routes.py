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

    # Check if the uploaded file is raw PCM (no RIFF header and ends with .wav)
    if len(audio_bytes) > 0 and not audio_bytes.startswith(b'RIFF') and ext == '.wav':
        import struct
        pcm_size = len(audio_bytes)
        header = struct.pack('<4sI4s', b'RIFF', 36 + pcm_size, b'WAVE')
        fmt = struct.pack('<4sIHHIIHH', b'fmt ', 16, 1, 1, 16000, 32000, 2, 16)
        data_hdr = struct.pack('<4sI', b'data', pcm_size)
        audio_bytes = header + fmt + data_hdr + audio_bytes

    if len(audio_bytes) > settings.VOICE_MAX_SIZE:
        raise HTTPException(400, "Audio file too large (max 25MB)")

    text = voice_service.transcribe(audio_bytes, file.filename)

    categorization_service = CategorizationService(db)

    result = categorization_service.extract(text, user_id)

    return result

