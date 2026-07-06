from pydantic import BaseModel
from typing import List, Optional
import uuid
from spendoo.statistics.models import (
    BudgetStatusResponse,
    Granularity,
    BudgetStatus,
    StatsBucketDto,
    BudgetStatusBucketDto,
    TopCategoriesResponse,
)
from pydantic import AwareDatetime
from decimal import Decimal

class ForecastRequest(BaseModel):
    user_id: uuid.UUID
    granularity: Granularity
    start_date: AwareDatetime
    end_date: AwareDatetime
    category_id: Optional[uuid.UUID] = None  # if None, forecast all categories combined

class ForecastBucketDto(BaseModel):
    spending: Decimal
    income: Decimal = Decimal("0.00")  # always 0 for predicted
    budget: Decimal
    start_date: AwareDatetime
    predicted: bool

class ForecastResponse(BaseModel):
    buckets: List[ForecastBucketDto]
    highest_spending_bucket_index: int
    highest_value: Decimal
    predict: bool = True

class CombinedForecastBucketDto(BaseModel):
    spending:          Decimal
    income:            Decimal = Decimal("0.00")
    budget:            Decimal
    start_date:        AwareDatetime
    predicted:         bool
    status:  Optional[BudgetStatus] = None  # None for history buckets

class FinancialStatsForecastResponse(BaseModel):
    buckets:                       List[CombinedForecastBucketDto]
    highest_spending_bucket_index: int
    highest_value:                 Decimal
    predict:                       bool

class CombinedForecastResponse(BaseModel):
    financial_stats_forecast: FinancialStatsForecastResponse
    budget_status: BudgetStatusResponse
    top_categories: TopCategoriesResponse