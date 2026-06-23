from pydantic import BaseModel
from typing import List, Optional
import uuid
from spendoo.statistics.models import Granularity
from datetime import datetime
from decimal import Decimal

class ForecastRequest(BaseModel):
    user_id: uuid.UUID
    granularity: Granularity
    start_date: datetime
    end_date: datetime

class ForecastBucketDto(BaseModel):
    spending: Decimal
    income: Decimal = Decimal("0.00")  # always 0 for predicted
    budget: Decimal
    start_date: datetime
    predicted: bool

class ForecastResponse(BaseModel):
    buckets: List[ForecastBucketDto]
    highest_spending_bucket_index: int
    highest_value: Decimal
    message: Optional[str] = None