from spendoo.chatbot.tools.base import BaseTool
from spendoo.forecasting.service import ForecastService
from spendoo.forecasting.models import ForecastRequest
from spendoo.statistics.models import Granularity
from datetime import datetime
import uuid
from sqlalchemy.orm import Session

class ForecastStatsTool(BaseTool):
    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "forecast_stats",
                "description": "Forecast future spending based on past data using time series analysis.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": "Start date of historical data to use in ISO format (YYYY-MM-DD)."
                        },
                        "end_date": {
                            "type": "string",
                            "description": "End date of the desired forecast horizon in ISO format (YYYY-MM-DD)."
                        },
                        "granularity": {
                            "type": "string",
                            "enum": ["DAY", "WEEK", "MONTH", "YEAR"],
                            "description": "The granularity of the forecasted buckets."
                        },
                        "category_id": {
                            "type": "string",
                            "description": "Optional specific category UUID to forecast. If omitted, forecasts total combined spending."
                        }
                    },
                    "required": ["start_date", "end_date", "granularity"]
                }
            }
        }

    def execute(self, db: Session, user_id: uuid.UUID, **kwargs) -> str:
        req = ForecastRequest(
            user_id=user_id,
            granularity=Granularity[kwargs["granularity"]],
            start_date=datetime.fromisoformat(kwargs["start_date"]),
            end_date=datetime.fromisoformat(kwargs["end_date"]),
            category_id=uuid.UUID(kwargs["category_id"]) if kwargs.get("category_id") else None
        )
        service = ForecastService(db)
        result = service.forecast_buckets(req)
        return result.model_dump_json()
