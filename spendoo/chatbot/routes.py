from fastapi import APIRouter

router = APIRouter(prefix="/chatbot", tags=["chatbot"])


@router.get("/")
def info():
    return {"module": "chatbot", "status": "ok"}


@router.get("/health")
def health():
    return {"status": "ok"}
