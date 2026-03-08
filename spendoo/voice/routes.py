from fastapi import APIRouter

router = APIRouter(prefix="/voice", tags=["voice"])


@router.get("/")
def info():
    return {"module": "voice", "status": "ok"}


@router.get("/health")
def health():
    return {"status": "ok"}
