import numpy as np
import pandas as pd
from datetime import timedelta
from darts import TimeSeries
from darts.models import Theta
from sqlalchemy.orm import Session

from spendoo.anomaly_detection.service import AnomalyService
from .repository import ForecastRepository
from .validators import validate_spending_series, SparsityError
from .models import ForecastResponse


class ForecastService:
    def __init__(self, db: Session):
        self.repo    = ForecastRepository(db)
        self.anomaly = AnomalyService(db)

    def forecast(self, user_id, horizon: int = 10, lookback: int = 20) -> ForecastResponse:

        # ── 1. Pull data ─────────────────────────────────────────────────────
        daily = self.repo.get_daily_spending(user_id, lookback)

        # ── 2. Validate — reject sparse data before doing anything ───────────
        try:
            validate_spending_series(daily)
        except SparsityError as e:
            return ForecastResponse(
                forecast_dates=[],
                forecast_values=[],
                horizon_days=horizon,
                trained_on_days=0,
                message=str(e)
            )

        # ── 3. Clean via anomaly detection ───────────────────────────────────
        anomaly_result = self.anomaly.detect(user_id, days=lookback)

        if anomaly_result.cleaned_values:
            cleaned = pd.Series(
                anomaly_result.cleaned_values,
                index=daily.index
            )
        else:
            cleaned = daily   # fallback: anomaly module returned empty (too sparse)

        # ── 4. Fit Theta ─────────────────────────────────────────────────────
        try:
            train_darts = TimeSeries.from_series(cleaned)
            model = Theta(seasonality_period=7)
            model.fit(train_darts)
        except Exception as e:
            return ForecastResponse(
                forecast_dates=[],
                forecast_values=[],
                horizon_days=horizon,
                trained_on_days=len(cleaned),
                message=f"Model training failed: {str(e)}"
            )

        # ── 5. Predict ───────────────────────────────────────────────────────
        prediction     = model.predict(horizon)
        forecast_vals  = prediction.values().flatten().tolist()

        last_date      = daily.index[-1]
        forecast_dates = [
            (last_date + timedelta(days=i + 1)).strftime("%Y-%m-%d")
            for i in range(horizon)
        ]

        return ForecastResponse(
            forecast_dates=forecast_dates,
            forecast_values=forecast_vals,
            horizon_days=horizon,
            trained_on_days=len(cleaned),
            message=None
        )