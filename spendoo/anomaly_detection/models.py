from pydantic import BaseModel, field_validator
from typing import List, Optional
import uuid


class AnomalyRequest(BaseModel):
    user_id: uuid.UUID
    days: int = 30   # how many recent days to analyze (20-30 typical)
    
    @field_validator("days")
    @classmethod
    def days_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("days must be a positive integer greater than 0")
        return v

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