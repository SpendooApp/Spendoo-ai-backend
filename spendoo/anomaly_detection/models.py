from pydantic import BaseModel
from typing import List, Optional
import uuid


class AnomalyRequest(BaseModel):
    user_id: uuid.UUID
    days: int = 30   # how many recent days to analyze (20-30 typical)

class AnomalyResponse(BaseModel):
    dates:          List[str]
    original_values: List[float]
    cleaned_values:  List[float]
    is_anomaly:      List[bool]
    anomaly_dates:   List[str]
    anomaly_count:   int
    lower_bound:     float
    upper_bound:     float
    message:         Optional[str] = None