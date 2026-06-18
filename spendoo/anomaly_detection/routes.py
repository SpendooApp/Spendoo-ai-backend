from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from spendoo.core.database import get_db
from .models import AnomalyRequest, AnomalyResponse
from .service import AnomalyService

router = APIRouter(prefix="/anomaly", tags=["Anomaly Detection"])

@router.post("/detect", response_model=AnomalyResponse)
def detect_anomalies(request: AnomalyRequest, db: Session = Depends(get_db)):
    service = AnomalyService(db)
    return service.detect(request.user_id, request.days)