from spendoo.chatbot.tools.base import BaseTool
import uuid
import json
from sqlalchemy.orm import Session
from spendoo.chatbot.repository import get_notifications

class GetNotificationsTool(BaseTool):
    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "get_notifications",
                "description": "Fetch the user's recent notifications.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Max number of notifications to return (default 20)."
                        }
                    },
                    "required": []
                }
            }
        }

    def execute(self, db: Session, user_id: uuid.UUID, **kwargs) -> str:
        limit = kwargs.get("limit", 20)
        notifications = get_notifications(db, user_id, limit)
        result = []
        for n in notifications:
            result.append({
                "id": str(n.id),
                "title": n.title,
                "message": n.message,
                "type": n.type,
                "is_read": n.is_read,
                "sent_at": n.sent_at.isoformat() if n.sent_at else None
            })
        return json.dumps(result)
