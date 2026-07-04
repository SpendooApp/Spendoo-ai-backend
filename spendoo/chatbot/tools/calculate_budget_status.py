from spendoo.chatbot.tools.base import BaseTool
from spendoo.statistics.service import StatisticsService
from spendoo.statistics.models import Granularity
from datetime import datetime
import uuid
from sqlalchemy.orm import Session

class CalculateBudgetStatusTool(BaseTool):
    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "calculate_budget_status",
                "description": "Fetch the budget status (percentage consumed) over a time range.",
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
                            "description": "The granularity of the buckets."
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
        result = service.calculate_budget_status(user_id, granularity, start_date, end_date)
        return result.model_dump_json()
