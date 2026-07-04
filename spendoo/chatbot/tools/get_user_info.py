from spendoo.chatbot.tools.base import BaseTool
import uuid
from sqlalchemy.orm import Session
from spendoo.chatbot.repository import get_user_info

class GetUserInfoTool(BaseTool):
    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "get_user_info",
                "description": "Fetch the basic profile and information of the current user.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

    def execute(self, db: Session, user_id: uuid.UUID, **kwargs) -> str:
        user = get_user_info(db, user_id)
        if not user:
            return "User not found."
        return str({
            "full_name": user.full_name,
            "email": user.email,
            "gender": user.gender,
            "birth_date": user.birth_date.isoformat(),
            "is_verified": user.is_verified,
            "created_at": user.created_at.isoformat()
        })
