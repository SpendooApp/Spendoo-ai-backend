from fastapi import APIRouter

router = APIRouter(prefix="/ocr", tags=["ocr"])


@router.get("/")
def info():
    return {"module": "ocr", "status": "ok"}


@router.get("/health")
def health():
    return {"status": "ok"}
