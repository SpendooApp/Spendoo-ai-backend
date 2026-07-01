from spendoo.chatbot.tools.base import BaseTool
import uuid
import json
from sqlalchemy.orm import Session
from spendoo.chatbot.repository import get_achievements

class GetAchievementsTool(BaseTool):
    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "get_achievements",
                "description": "Fetch the achievements the user has unlocked.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

    def execute(self, db: Session, user_id: uuid.UUID, **kwargs) -> str:
        achievements = get_achievements(db, user_id)
        result = []
        for ua, a in achievements:
            result.append({
                "user_achievement_id": str(ua.id),
                "achievement_id": str(a.id),
                "code": a.code,
                "title_en": a.title_en,
                "description_en": a.description_en,
                "level": a.level,
                "unlocked_at": ua.unlocked_at.isoformat() if ua.unlocked_at else None
            })
        return json.dumps(result)
