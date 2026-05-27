from spendoo.core.database import get_db
from .service import CategorizationService
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from .models import CategorizationRequest


router = APIRouter(prefix="/categorization", tags=["categorization"])


@router.post("/categorize")
def categorize(request: CategorizationRequest, db: Session = Depends(get_db)):
    service = CategorizationService(db)
    result = service.extract(request.text, request.user_id)
    return result


# http://127.0.0.1:8000/api/v1/categorization/categorize


@router.get("/health")
def health():
    return {"status": "ok"}
