from spendoo.chatbot.tools.base import BaseTool
import uuid
import json
from sqlalchemy.orm import Session
from spendoo.chatbot.repository import get_saving_goals

class GetSavingGoalsTool(BaseTool):
    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "get_saving_goals",
                "description": "Fetch the user's saving goals and their statuses.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

    def execute(self, db: Session, user_id: uuid.UUID, **kwargs) -> str:
        goals = get_saving_goals(db, user_id)
        result = []
        for g in goals:
            result.append({
                "id": str(g.id),
                "goal_name": g.goal_name,
                "priority": g.priority,
                "deadline": g.deadline.isoformat() if g.deadline else None,
                "target_amount": float(g.target_amount),
                "is_completed": g.is_completed
            })
        return json.dumps(result)
