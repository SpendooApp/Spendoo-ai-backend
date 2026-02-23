from pydantic import BaseModel
from enum import Enum
from typing import List

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
    miscellaneous = "miscellaneous"
    other = "other"

class TransactionItem(BaseModel):
    item_name: str
    quantity: int
    unit_price: float
    total_price: float
    category: CategoryEnum

class TransactionExtractionResponse(BaseModel):
    items: List[TransactionItem]
    grand_total: float

class CategorizationRequest(BaseModel):
    text: str
