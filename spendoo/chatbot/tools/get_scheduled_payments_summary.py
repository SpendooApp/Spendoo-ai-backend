from spendoo.chatbot.tools.base import BaseTool
import uuid
import json
from sqlalchemy.orm import Session
from spendoo.chatbot.repository import get_scheduled_payments_summary

class GetScheduledPaymentsSummaryTool(BaseTool):
    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "get_scheduled_payments_summary",
                "description": "Fetch the user's scheduled payments dashboard summary (total scheduled amount and upcoming count).",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

    def execute(self, db: Session, user_id: uuid.UUID, **kwargs) -> str:
        summary = get_scheduled_payments_summary(db, user_id)
        summary["total_scheduled_amount"] = float(summary["total_scheduled_amount"]) if summary["total_scheduled_amount"] is not None else 0.0
        return json.dumps(summary)
