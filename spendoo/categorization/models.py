from pydantic import BaseModel
from enum import Enum
from typing import List, Optional
from spendoo.categorization.repository import CategorizationRepository as repo


categories = repo().get_all_categories()

category_block = "\n".join(
    f"{c['id']} {c['name']}"
    for c in categories
)

# 1 Groceries
# 2 Entertainment
# 3 Utilities
# 4 Transportation
# 5 Food
# 6 Health
# 7 Education
# 8 Shopping
# 9 Other

class TransactionItem(BaseModel):
    id: int
    item_name: str
    quantity: int
    unit_price: float
    total_price: float
    category: Optional[str] = None
    category_id: Optional[int] = None

class TransactionExtractionResponse(BaseModel):
    items: List[TransactionItem]
    grand_total: float

class CategorizationRequest(BaseModel):
    text: str
