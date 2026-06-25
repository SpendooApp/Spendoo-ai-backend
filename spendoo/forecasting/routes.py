from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from spendoo.core.database import get_db
from .models import CombinedForecastResponse, ForecastRequest, ForecastResponse
from .service import ForecastService
from spendoo.statistics.models import StatsRequest

router = APIRouter(prefix="/forecasting", tags=["Forecasting"])

@router.post("/predict", response_model=ForecastResponse)
def predict(request: ForecastRequest, db: Session = Depends(get_db)):
    service = ForecastService(db)
    return service.forecast_buckets(request)


@router.post("/predict-combined", response_model=CombinedForecastResponse)
def predict(request: StatsRequest, db: Session = Depends(get_db)):
    service = ForecastService(db)
    return service.forecast_buckets_combined(request)
