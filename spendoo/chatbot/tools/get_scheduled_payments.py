from spendoo.chatbot.tools.base import BaseTool
import uuid
import json
from sqlalchemy.orm import Session
from spendoo.chatbot.repository import get_scheduled_payments

class GetScheduledPaymentsTool(BaseTool):
    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "get_scheduled_payments",
                "description": "Fetch the user's scheduled or recurring payments.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

    def execute(self, db: Session, user_id: uuid.UUID, **kwargs) -> str:
        payments = get_scheduled_payments(db, user_id)
        result = []
        for p in payments:
            result.append({
                "id": str(p.id),
                "title": p.title,
                "amount": float(p.amount),
                "start_date": p.start_date.isoformat() if p.start_date else None,
                "next_due_date": p.next_due_date.isoformat() if p.next_due_date else None,
                "frequency_days": p.frequency,
                "category_id": str(p.category_id)
            })
        return json.dumps(result)
