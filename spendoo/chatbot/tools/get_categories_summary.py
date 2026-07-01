from spendoo.chatbot.tools.base import BaseTool
import uuid
import json
from sqlalchemy.orm import Session
from spendoo.chatbot.repository import get_categories_summary

class GetCategoriesSummaryTool(BaseTool):
    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "get_categories_summary",
                "description": "Fetch the user's categorized spending summary (total budget, total spent within active budgets, and added unassigned income).",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

    def execute(self, db: Session, user_id: uuid.UUID, **kwargs) -> str:
        summary = get_categories_summary(db, user_id)
        for k in summary:
            summary[k] = float(summary[k]) if summary[k] is not None else 0.0
        return json.dumps(summary)
