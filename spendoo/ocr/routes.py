import uuid

from fastapi import APIRouter, Depends, UploadFile, HTTPException
from spendoo.core.database import get_db
from spendoo.ocr.pipeline import ReceiptPipeline
from sqlalchemy.orm import Session

router = APIRouter(prefix="/ocr", tags=["OCR"])

pipeline = ReceiptPipeline()

@router.post("/scan/{user_id}")
async def scan_receipt(file: UploadFile, user_id: uuid.UUID, db: Session = Depends(get_db)):

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")
    
    image_bytes = await file.read()

    result = pipeline.process_receipt(image_bytes, db, user_id)

    return result
