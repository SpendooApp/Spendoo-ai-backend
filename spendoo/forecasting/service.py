import numpy as np
import pandas as pd
from datetime import timedelta, datetime, timezone
from darts import TimeSeries
from darts.models import Theta
from darts.utils.utils import SeasonalityMode
from sqlalchemy.orm import Session
from decimal import Decimal

from spendoo.forecasting.validators import validate_forecast_ratio, SparsityError
from spendoo.statistics.service import StatisticsService
from spendoo.statistics.models import Granularity
from spendoo.anomaly_detection.service import AnomalyService
from .models import ForecastRequest, ForecastResponse, ForecastBucketDto

GRANULARITY_SEASONALITY = {
    Granularity.DAY:   7,
    Granularity.WEEK:  4,
    Granularity.MONTH: 12,
    Granularity.YEAR:  1,
}

# How many days each granularity bucket spans — used for horizon calculation
GRANULARITY_DAYS = {
    Granularity.DAY:   1,
    Granularity.WEEK:  7,
    Granularity.MONTH: 30,
    Granularity.YEAR:  365,
}


class ForecastService:
    def __init__(self, db: Session):
        self.stats_service = StatisticsService(db)
        self.anomaly = AnomalyService(db)

    def forecast_buckets(self, request: ForecastRequest) -> ForecastResponse:
        granularity = request.granularity
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        horizon = request.end_date - datetime.now(timezone.utc)
        horizon = max(1, (horizon.days // GRANULARITY_SEASONALITY[granularity]))

        # ── 1.1 Cut history at last COMPLETED bucket, not at now ─────────────────
        last_completed_start = self._get_last_completed_bucket_start(now, granularity)

        # End of history = start of current (incomplete) bucket
        # e.g. for WEEK granularity on June 23: history ends at June 21 (start of current week)
        # so June 21 week is excluded from history and becomes a predicted bucket
        if granularity == Granularity.DAY:
            history_end = last_completed_start + timedelta(days=1)
        elif granularity == Granularity.WEEK:
            history_end = last_completed_start + timedelta(weeks=1)
        elif granularity == Granularity.MONTH:
            if last_completed_start.month == 12:
                history_end = last_completed_start.replace(year=last_completed_start.year + 1, month=1, day=1)
            else:
                history_end = last_completed_start.replace(month=last_completed_start.month + 1, day=1)
        elif granularity == Granularity.YEAR:
            history_end = last_completed_start.replace(year=last_completed_start.year + 1)
        else:
            history_end = last_completed_start + timedelta(days=1)

        # ── 1.2. Get history buckets from StatisticsService (same structure as /calculate) 
        history_response = self.stats_service.calculate_stats(
            user_id=request.user_id,
            granularity=granularity,
            start_date=request.start_date,
            end_date=history_end
        )
        history_buckets = history_response.buckets

        # ── 1.3. Calculate horizon from now → end_date ─────────────────────────────
        forecast_end = request.end_date.replace(tzinfo=None)
        delta   = forecast_end - history_end  # from end of last completed bucket to requested end_date
        divisor = GRANULARITY_DAYS[granularity]  
        horizon = max(1, delta.days // divisor)

        # ── 1.4. Validate ratio ────────────────────────────────────────────────────
        try:
            validate_forecast_ratio(len(history_buckets), horizon)
        except SparsityError as e:
            result_buckets = [
                ForecastBucketDto(
                    spending=b.spending, income=b.income,
                    budget=b.budget, start_date=b.start_date, predicted=False
                )
                for b in history_buckets
            ]
            return ForecastResponse(
                buckets=result_buckets,
                highest_spending_bucket_index=int(history_response.highest_spending_bucket_index),
                highest_value=history_response.highest_value,
                message=str(e)
            )
        
        # ── 2. Build history bucket DTOs (predicted=False, same shape as stats response)
        result_buckets = [
            ForecastBucketDto(
                spending=b.spending,
                income=b.income,
                budget=b.budget,
                start_date=b.start_date,
                predicted=False
            )
            for b in history_buckets
        ]

        # ── 3. Build Series for spending and budget separately
        dates = [b.start_date for b in history_buckets]
        spending_vals = pd.Series([float(b.spending) for b in history_buckets], index=pd.to_datetime(dates))
        budget_vals = pd.Series([float(b.budget) for b in history_buckets], index=pd.to_datetime(dates))

        # ── 4. Clean spending anomalies (budget is deterministic — no IQR needed)
        cleaned_spending = self.anomaly.clean_series(spending_vals)

        # ── 5. Forecast spending and budget
        forecast_spending = self._fit_and_forecast(cleaned_spending, horizon, granularity)
        forecast_budget = self._fit_and_forecast(budget_vals, horizon, granularity)

        # ── 6. Generate future bucket start dates
        future_dates = self._generate_future_dates(dates[-1], granularity, horizon)

        # ── 7. Append predicted buckets
        for val_s, val_b, fd in zip(forecast_spending, forecast_budget, future_dates):
            result_buckets.append(ForecastBucketDto(
                spending=Decimal(str(round(val_s, 2))),
                income=Decimal("0.00"),
                budget=Decimal(str(round(val_b, 2))),
                start_date=fd,
                predicted=True
            ))

        # ── 8. Recalculate highest_spending_bucket_index and highest_value across all buckets
        highest_spending_idx = max(
            range(len(result_buckets)),
            key=lambda i: result_buckets[i].spending
        )
        highest_value = max(
            max(b.spending, b.income + b.budget)
            for b in result_buckets
        )

        return ForecastResponse(
            buckets=result_buckets,
            highest_spending_bucket_index=highest_spending_idx,
            highest_value=highest_value,
            message=None
        )
    

    def _fit_and_forecast(
        self,
        series: pd.Series,
        horizon: int,
        granularity: Granularity
    ) -> np.ndarray:
        seasonality_period = GRANULARITY_SEASONALITY.get(granularity, 7)

        # Theta needs more points than the seasonality period
        if len(series) <= seasonality_period:
            seasonality_period = 1

        darts_series = TimeSeries.from_series(series)
        model = Theta(seasonality_period=seasonality_period, season_mode=SeasonalityMode.ADDITIVE)
        model.fit(darts_series)

        forecast = model.predict(horizon).values().flatten()
        return np.clip(forecast, a_min=0, a_max=None)   # spending and budget can't be negative


    def _generate_future_dates(
        self,
        last_date: datetime,
        granularity: Granularity,
        horizon: int
    ) -> list[datetime]:
        dates = []
        curr  = last_date
        for _ in range(horizon):
            if granularity == Granularity.DAY:
                curr = curr + timedelta(days=1)
            elif granularity == Granularity.WEEK:
                curr = curr + timedelta(weeks=1)
            elif granularity == Granularity.MONTH:
                month = curr.month + 1
                year  = curr.year
                if month > 12:
                    month = 1
                    year += 1
                curr = curr.replace(year=year, month=month, day=1)
            elif granularity == Granularity.YEAR:
                curr = curr.replace(year=curr.year + 1)
            dates.append(curr)
        return dates
    

    def _get_last_completed_bucket_start(self, now: datetime, granularity: Granularity) -> datetime:
        """Returns the start of the most recently COMPLETED bucket — not the current one."""
        if granularity == Granularity.DAY:
            # yesterday
            return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif granularity == Granularity.WEEK:
            # start of last week (week that ended before current week started)
            days_since_sunday = (now.weekday() + 1) % 7
            current_week_start = (now - timedelta(days=days_since_sunday)).replace(hour=0, minute=0, second=0, microsecond=0)
            return current_week_start - timedelta(weeks=1)
        elif granularity == Granularity.MONTH:
            # first day of last month
            if now.month == 1:
                return now.replace(year=now.year - 1, month=12, day=1, hour=0, minute=0, second=0, microsecond=0)
            return now.replace(month=now.month - 1, day=1, hour=0, minute=0, second=0, microsecond=0)
        elif granularity == Granularity.YEAR:
            return now.replace(year=now.year - 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return now



    # def forecast(self, user_id, horizon: int = 10, lookback: int = 20) -> ForecastResponse:

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