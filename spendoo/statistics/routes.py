from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from spendoo.core.database import get_db
from spendoo.statistics.models import StatsRequest, FinancialStatsResponse
from spendoo.statistics.service import StatisticsService

router = APIRouter(prefix="/statistics", tags=["statistics"])

@router.post("/calculate", response_model=FinancialStatsResponse)
def calculate_statistics(request: StatsRequest, db: Session = Depends(get_db)):
    service = StatisticsService(db)
    return service.calculate_stats(
        user_id=request.user_id,
        granularity=request.granularity,
        start_date=request.start_date,
        end_date=request.end_date
    )
