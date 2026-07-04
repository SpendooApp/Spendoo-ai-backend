from spendoo.chatbot.tools.base import BaseTool
from datetime import datetime
import uuid
import json
from sqlalchemy.orm import Session
from spendoo.chatbot.repository import get_transactions

class GetTransactionsTool(BaseTool):
    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "get_transactions",
                "description": "Fetch the user's transactions. Automatically filters out unclassified negative transactions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Max number of transactions to return (default 50)."
                        },
                        "start_date": {
                            "type": "string",
                            "description": "Optional start date in ISO format (YYYY-MM-DD)."
                        },
                        "end_date": {
                            "type": "string",
                            "description": "Optional end date in ISO format (YYYY-MM-DD)."
                        }
                    },
                    "required": []
                }
            }
        }

    def execute(self, db: Session, user_id: uuid.UUID, **kwargs) -> str:
        limit = kwargs.get("limit", 50)
        start_date = datetime.fromisoformat(kwargs["start_date"]) if kwargs.get("start_date") else None
        end_date = datetime.fromisoformat(kwargs["end_date"]) if kwargs.get("end_date") else None
        
        transactions = get_transactions(db, user_id, limit, start_date, end_date)
        
        result = []
        for t in transactions:
            result.append({
                "id": str(t.id),
                "amount": float(t.amount),
                "date": t.transaction_date.isoformat(),
                "title": t.title,
                "note": t.note,
                "category_id": str(t.category_id) if t.category_id else None
            })
        return json.dumps(result)
