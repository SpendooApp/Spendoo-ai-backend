from fastapi import APIRouter, UploadFile, HTTPException
from spendoo.ocr.pipeline import ReceiptPipeline

router = APIRouter(prefix="/ocr", tags=["OCR"])

pipeline = ReceiptPipeline()

@router.post("/scan")
async def scan_receipt(file: UploadFile):

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an image.")
    
    image_bytes = await file.read()

    result = pipeline.process_receipt(image_bytes)

    return result
