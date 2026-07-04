from spendoo.chatbot.tools.base import BaseTool
import uuid
import json
from sqlalchemy.orm import Session
from spendoo.chatbot.repository import get_top_frequency_items

class GetTopFrequencyItemsTool(BaseTool):
    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "get_top_frequency_items",
                "description": "Fetch the user's top spending items (transactions grouped by title and category) sorted by frequency of occurrence.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Max number of items to return (default 5)."
                        }
                    },
                    "required": []
                }
            }
        }

    def execute(self, db: Session, user_id: uuid.UUID, **kwargs) -> str:
        limit = kwargs.get("limit", 5)
        items = get_top_frequency_items(db, user_id, limit)
        return json.dumps(items)
