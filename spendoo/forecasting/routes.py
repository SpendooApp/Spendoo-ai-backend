from fastapi import APIRouter

router = APIRouter(prefix="/forecasting", tags=["forecasting"])


@router.get("/")
def info():
    return {"module": "forecasting", "status": "ok"}


@router.get("/health")
def health():
    return {"status": "ok"}
