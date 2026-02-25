from pydantic import BaseModel
from enum import Enum
from typing import List, Optional

class CategoryEnum(str, Enum):
    groceries = "groceries"
    food = "food"
    drinks = "drinks"
    shopping = "shopping"
    entertainment = "entertainment"
    utilities = "utilities"
    transportation = "transportation"
    healthcare = "healthcare"
    education = "education"
    personal_care = "personal care"
    clothing = "clothing"
    # miscellaneous = "miscellaneous"
    # other = "other"

CATEGORY_ID_MAP = {
    "groceries": 1,
    "food": 2,
    "drinks": 3,
    "shopping": 4,
    "entertainment": 5,
    "utilities": 6,
    "transportation": 7,
    "healthcare": 8,
    "education": 9,
    "personal care": 10,
    "clothing": 11
}

class TransactionItem(BaseModel):
    id: int
    item_name: str
    quantity: int
    unit_price: float
    total_price: float
    category: Optional[CategoryEnum] = None
    category_id: Optional[int] = None

class TransactionExtractionResponse(BaseModel):
    items: List[TransactionItem]
    grand_total: float

class CategorizationRequest(BaseModel):
    text: str
