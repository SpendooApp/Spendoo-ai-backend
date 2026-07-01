from spendoo.chatbot.tools.base import BaseTool
from spendoo.statistics.service import StatisticsService
from spendoo.statistics.models import Granularity
import uuid
from sqlalchemy.orm import Session

class GetTopCategoriesTool(BaseTool):
    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "get_top_categories",
                "description": "Fetch the user's top spending categories for a given granularity.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "granularity": {
                            "type": "string",
                            "enum": ["DAY", "WEEK", "MONTH", "YEAR"],
                            "description": "The time period to fetch categories for."
                        }
                    },
                    "required": ["granularity"]
                }
            }
        }

    def execute(self, db: Session, user_id: uuid.UUID, **kwargs) -> str:
        granularity = Granularity[kwargs["granularity"]]
        
        service = StatisticsService(db)
        result = service.get_top_categories(user_id, granularity)
        return result.model_dump_json()
