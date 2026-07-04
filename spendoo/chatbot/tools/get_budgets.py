from spendoo.chatbot.tools.base import BaseTool
import uuid
import json
from sqlalchemy.orm import Session
from spendoo.chatbot.repository import get_budgets

class GetBudgetsTool(BaseTool):
    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "get_budgets",
                "description": "Fetch the user's active budgets.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

    def execute(self, db: Session, user_id: uuid.UUID, **kwargs) -> str:
        budgets = get_budgets(db, user_id)
        result = []
        for b in budgets:
            result.append({
                "id": str(b.id),
                "category_id": str(b.category_id),
                "amount": float(b.amount),
                "period": b.period,
                "start_date": b.start_date.isoformat() if b.start_date else None,
                "end_date": b.end_date.isoformat() if b.end_date else None
            })
        return json.dumps(result)
