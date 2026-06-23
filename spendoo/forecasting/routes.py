from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from spendoo.core.database import get_db
from .models import ForecastRequest, ForecastResponse
from .service import ForecastService

router = APIRouter(prefix="/forecasting", tags=["Forecasting"])

@router.post("/predict", response_model=ForecastResponse)
def predict(request: ForecastRequest, db: Session = Depends(get_db)):
    service = ForecastService(db)
    return service.forecast_buckets(request)
