from spendoo.chatbot.tools.base import BaseTool
from spendoo.statistics.service import StatisticsService
from spendoo.statistics.models import Granularity
from datetime import datetime
import uuid
from sqlalchemy.orm import Session

class CalculateStatsTool(BaseTool):
    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "calculate_stats",
                "description": "Fetch overall financial statistics (spending, income, budget) over a specific time range.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date in ISO format (YYYY-MM-DD)."
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date in ISO format (YYYY-MM-DD)."
                        },
                        "granularity": {
                            "type": "string",
                            "enum": ["DAY", "WEEK", "MONTH", "YEAR"],
                            "description": "The granularity of the statistics buckets."
                        }
                    },
                    "required": ["start_date", "end_date", "granularity"]
                }
            }
        }

    def execute(self, db: Session, user_id: uuid.UUID, **kwargs) -> str:
        start_date = datetime.fromisoformat(kwargs["start_date"])
        end_date = datetime.fromisoformat(kwargs["end_date"])
        granularity = Granularity[kwargs["granularity"]]
        
        service = StatisticsService(db)
        result = service.calculate_stats(user_id, granularity, start_date, end_date)
        return result.model_dump_json()
