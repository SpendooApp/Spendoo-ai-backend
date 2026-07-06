from pydantic import BaseModel
from typing import List
from pydantic import AwareDatetime
from enum import Enum
import uuid
from decimal import Decimal

class Granularity(str, Enum):
    DAY = "DAY"
    WEEK = "WEEK"
    MONTH = "MONTH"
    YEAR = "YEAR"

class StatsRequest(BaseModel):
    user_id: uuid.UUID
    granularity: Granularity
    start_date: AwareDatetime
    end_date: AwareDatetime

class StatsBucketDto(BaseModel):
    spending: Decimal
    income: Decimal
    budget: Decimal
    start_date: AwareDatetime

class FinancialStatsResponse(BaseModel):
    buckets: List[StatsBucketDto]
    highest_spending_bucket_index: int
    highest_value: Decimal

class BudgetStatus(str, Enum):
    WITHIN = "within"
    RISK = "risk"
    OVERSPEND = "overspend"

class BudgetStatusBucketDto(BaseModel):
    spending: Decimal
    status: BudgetStatus
    percentage: Decimal
    start_date: AwareDatetime

class BudgetStatusResponse(BaseModel):
    buckets: List[BudgetStatusBucketDto]
    highest_spending: Decimal

class CategorySpendingDto(BaseModel):
    category_id: uuid.UUID
    category_name: str
    category_icon: str
    spending: Decimal
    percentage_change: Decimal
    contribution_percentage: Decimal

class TopCategoriesResponse(BaseModel):
    total_spending: Decimal
    top_categories: List[CategorySpendingDto]

class CombinedStatsResponse(BaseModel):
    financial_stats: FinancialStatsResponse
    budget_status: BudgetStatusResponse
    top_categories: TopCategoriesResponse


