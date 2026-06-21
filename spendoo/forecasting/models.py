from pydantic import BaseModel
from typing import List, Optional
import uuid

class ForecastRequest(BaseModel):
    user_id: uuid.UUID
    horizon: int = 10        # days to predict forward
    lookback: int = 20       # days of history to train on

class ForecastResponse(BaseModel):
    forecast_dates:  List[str]
    forecast_values: List[float]
    horizon_days:    int
    trained_on_days: int
    message:         Optional[str] = None