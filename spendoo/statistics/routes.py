from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import uuid

from spendoo.core.database import get_db
from spendoo.statistics.models import (
    StatsRequest,
    FinancialStatsResponse,
    BudgetStatusResponse,
    TopCategoriesResponse,
    Granularity,
    CombinedStatsResponse
)
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

@router.post("/budget-status", response_model=BudgetStatusResponse)
def get_budget_status(request: StatsRequest, db: Session = Depends(get_db)):
    service = StatisticsService(db)
    return service.calculate_budget_status(
        user_id=request.user_id,
        granularity=request.granularity,
        start_date=request.start_date,
        end_date=request.end_date
    )

@router.get("/top-categories", response_model=TopCategoriesResponse)
def get_top_categories(user_id: uuid.UUID, granularity: Granularity, db: Session = Depends(get_db)):
    service = StatisticsService(db)
    return service.get_top_categories(
        user_id=user_id,
        granularity=granularity
    )

@router.post("/combined", response_model=CombinedStatsResponse)
def get_combined_statistics(request: StatsRequest, db: Session = Depends(get_db)):
    service = StatisticsService(db)
    return service.calculate_combined_stats(
        user_id=request.user_id,
        granularity=request.granularity,
        start_date=request.start_date,
        end_date=request.end_date
    )


