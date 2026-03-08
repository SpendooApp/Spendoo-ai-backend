from fastapi import APIRouter

router = APIRouter(prefix="/core", tags=["core"])


@router.get("/")
def index():
    return "Hello World!"


@router.get("/health")
def health():
    return {"status": "ok"}
