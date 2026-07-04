from flask import json

from spendoo.chatbot.tools.base import BaseTool
from spendoo.forecasting.service import ForecastService
from spendoo.forecasting.models import ForecastRequest
from spendoo.statistics.models import Granularity
from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import timedelta

class ForecastStatsTool(BaseTool):
    @property
    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": "forecast_stats",
                "description": (
                        "Forecast future spending and budget based on historical data. "
                        "IMPORTANT: start_date must go back far enough to provide sufficient history. "
                        "For WEEK granularity: start_date should be at least 10-12 weeks before today. "
                        "For MONTH granularity: start_date should be at least 10-12 months before today. "
                        "For DAY granularity: start_date should be at least 30-60 days before today. "
                        "end_date should be the future date the user wants to forecast up to. "
                    ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "start_date": {
                            "type": "string",
                            "description": (
                            "History start date in YYYY-MM-DD format. "
                            "Must be far enough in the past to provide at least 10 completed buckets. "
                            "WEEK: at least 10 weeks back. MONTH: at least 10 months back. DAY: at least 30 days back."
                        )
                            },
                        "end_date": {
                            "type": "string",
                            "description": "End date of the desired forecast horizon in ISO format (YYYY-MM-DD) - should be in the future."
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
        def _parse(date_str: str) -> datetime:
            """Parse ISO date string and strip timezone — returns naive datetime."""
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt.replace(tzinfo=None) 
        
        def _serialize(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

        req = ForecastRequest(
            user_id=user_id,
            granularity=Granularity[kwargs["granularity"]],
            start_date=_parse(kwargs["start_date"]),
            end_date=_parse(kwargs["end_date"]),
            category_id=uuid.UUID(kwargs["category_id"]) if kwargs.get("category_id") else None
        )

        service  = ForecastService(db)
        result   = service.forecast_buckets(req)
        data     = result.model_dump()

        if not data.get("predict"):
            history_count = len(data.get("buckets", []))
            return json.dumps({
                "predict": False,
                "_forecast_note": (
                    f"Prediction was not possible — only {history_count} history bucket(s) available. "
                    f"At least 10 are needed. Tell the user their history is too short to forecast."
                )
            }, default=_serialize)

        granularity = kwargs["granularity"]


        history_buckets   = [b for b in data["buckets"] if not b["predicted"]]
        predicted_buckets = [b for b in data["buckets"] if b["predicted"]]
        
        response_data = {
            "predict": True,
            "granularity": granularity,
            "history_summary": {
                "bucket_count": len(history_buckets),
                "date_range":   f"{history_buckets[0]['start_date']} to {history_buckets[-1]['start_date']}"
                                if history_buckets else "N/A",
                "avg_weekly_spending": round(
                    sum(float(b["spending"]) for b in history_buckets) / len(history_buckets), 2
                ) if history_buckets else 0
            },
            "predicted_buckets": predicted_buckets
        }

        return json.dumps(response_data, default=_serialize)