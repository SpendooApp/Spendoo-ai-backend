from pydantic import BaseModel
from typing import List
from datetime import datetime
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
    start_date: datetime
    end_date: datetime

class StatsBucketDto(BaseModel):
    spending: Decimal
    income: Decimal
    budget: Decimal
    start_date: datetime

class FinancialStatsResponse(BaseModel):
    buckets: List[StatsBucketDto]
    highest_spending_bucket_index: int
