from spendoo.chatbot.tools.base import BaseTool
import uuid
import json
from sqlalchemy.orm import Session
from spendoo.chatbot.repository import get_balance_summary

class GetBalanceSummaryTool(BaseTool):
    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "get_balance_summary",
                "description": "Fetch the user's overall balance summary (total balance, total income including budgets, and total expenses).",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

    def execute(self, db: Session, user_id: uuid.UUID, **kwargs) -> str:
        summary = get_balance_summary(db, user_id)
        # Convert numeric values to floats
        for k in summary:
            summary[k] = float(summary[k]) if summary[k] is not None else 0.0
        return json.dumps(summary)
