from spendoo.chatbot.tools.base import BaseTool
import uuid
import json
from sqlalchemy.orm import Session
from spendoo.chatbot.repository import get_categories

class GetCategoriesTool(BaseTool):
    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "get_categories",
                "description": "Fetch the user's spending categories.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

    def execute(self, db: Session, user_id: uuid.UUID, **kwargs) -> str:
        categories = get_categories(db, user_id)
        result = []
        for c in categories:
            result.append({
                "id": str(c.id),
                "name": c.category_name,
                "icon": c.category_icon,
                "priority": c.priority
            })
        return json.dumps(result)
