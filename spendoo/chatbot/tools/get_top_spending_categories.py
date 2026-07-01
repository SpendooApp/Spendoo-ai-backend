from spendoo.chatbot.tools.base import BaseTool
import uuid
import json
from sqlalchemy.orm import Session
from spendoo.chatbot.repository import get_top_spending_categories

class GetTopSpendingCategoriesTool(BaseTool):
    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "get_top_spending_categories",
                "description": "Fetch the user's overall top spending categories ranked by aggregate lifetime transaction amounts. Use this for general, non-temporal rankings of categories by total expense volume.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Max number of categories to return (default 5)."
                        }
                    },
                    "required": []
                }
            }
        }

    def execute(self, db: Session, user_id: uuid.UUID, **kwargs) -> str:
        limit = kwargs.get("limit", 5)
        categories = get_top_spending_categories(db, user_id, limit)
        return json.dumps(categories)
