import numpy as np
import pandas as pd
from datetime import timedelta, datetime, timezone
from darts import TimeSeries
from darts.models import Theta
from darts.utils.utils import SeasonalityMode
from sqlalchemy.orm import Session
from decimal import Decimal

from spendoo.forecasting.validators import validate_forecast_ratio, SparsityError, validate_spending_signal
from spendoo.statistics.service import StatisticsService
from spendoo.statistics.models import Granularity, StatsRequest
from spendoo.anomaly_detection.service import AnomalyService
from .models import CombinedForecastResponse, ForecastRequest, ForecastResponse, ForecastBucketDto, FinancialStatsForecastResponse, CombinedForecastBucketDto

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
        now        = datetime.now(timezone.utc).replace(tzinfo=None)
        end_date   = request.end_date.replace(tzinfo=None)   if request.end_date.tzinfo   else request.end_date
        start_date = request.start_date.replace(tzinfo=None) if request.start_date.tzinfo else request.start_date

        # horizon = request.end_date - now
        # horizon = max(1, (horizon.days // GRANULARITY_SEASONALITY[granularity]))

        # ── 1.1 Cut history at last COMPLETED bucket, not at now ─────────────────
        last_completed_start = self.stats_service._get_last_completed_bucket_start(now, granularity)

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
        MIN_HISTORY_BUCKETS = 10
        fallback_start = self._subtract_buckets(last_completed_start, granularity, MIN_HISTORY_BUCKETS)
        effective_start = min(start_date, fallback_start)   # take whichever is earlier

        history_response = self.stats_service.calculate_stats(
            user_id=request.user_id,
            granularity=granularity,
            start_date=effective_start,    # ← not start_date directly
            end_date=history_end,
            category_id=request.category_id
        )
        history_buckets = history_response.buckets

        # ── 1.3. Calculate horizon from now → end_date ─────────────────────────────
        delta   = end_date - history_end  # from end of last completed bucket to requested end_date
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
                predict=False
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
        spending_vals = [float(b.spending) for b in history_buckets]
        budget_vals   = [float(b.budget)   for b in history_buckets]

        spending_series = pd.Series(spending_vals, index=pd.to_datetime(dates))
        budget_series   = pd.Series(budget_vals,   index=pd.to_datetime(dates))

        # ── 3.1 Validate signal quality BEFORE attempting to forecast ─────────────
        try:
            validate_spending_signal(spending_vals, budget_vals)
        except SparsityError as e:
            return ForecastResponse(
                buckets=[
                    ForecastBucketDto(
                        spending=b.spending, income=b.income,
                        budget=b.budget, start_date=b.start_date, predicted=False
                    )
                    for b in history_buckets
                ],
                highest_spending_bucket_index=int(history_response.highest_spending_bucket_index),
                highest_value=history_response.highest_value,
                predict=False
            )

        # ── 4. Clean spending anomalies (budget is deterministic — no IQR needed)
        cleaned_spending = self.anomaly.clean_series(spending_series)

        # ── 5. Forecast spending and budget
        forecast_spending = self._fit_and_forecast(cleaned_spending, horizon, granularity)
        forecast_budget = self._fit_and_forecast(budget_series, horizon, granularity)

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
        highest_value = max(
            max(b.spending, b.income + b.budget)
            for b in result_buckets
        )

        return ForecastResponse(
            buckets=result_buckets,
            highest_spending_bucket_index=int(history_response.highest_spending_bucket_index),
            highest_value=highest_value,
            predict=True
        )


    def forecast_buckets_combined(self, request: StatsRequest) -> CombinedForecastResponse:
        granularity = request.granularity
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        horizon = request.end_date - datetime.now(timezone.utc)
        horizon = max(1, (horizon.days // GRANULARITY_SEASONALITY[granularity]))

        # ── 1. Cut history at last COMPLETED bucket, not at now ─────────────────
        last_completed_start = self.stats_service._get_last_completed_bucket_start(now, granularity)
        history_end = self.stats_service._get_next_bucket_start(last_completed_start, granularity)
        future_dates = self._generate_future_dates(history_end - timedelta(days=1), granularity, horizon)

        # ── 2. Get history buckets from StatisticsService (same structure as /calculate) 
        history_response = self.stats_service.calculate_combined_stats(
            user_id=request.user_id,
            granularity=granularity,
            start_date=request.start_date,
            end_date=request.end_date,
            now=now
        )

        history_buckets = history_response.financial_stats.buckets

        # ── 3. Calculate horizon from now → end_date ─────────────────────────────
        forecast_end = request.end_date.replace(tzinfo=None)
        delta = forecast_end - history_end  # from end of last completed bucket to requested end_date
        divisor = GRANULARITY_DAYS[granularity]  
        horizon = max(1, delta.days // divisor)

        # ── 4. Validate ratio ────────────────────────────────────────────────────
        try:
            validate_forecast_ratio(len(history_buckets), horizon)
        except SparsityError as e:
            result_buckets = [
                CombinedForecastBucketDto(
                    spending=b.spending, income=b.income,
                    budget=b.budget, start_date=b.start_date, predicted=False
                )
                for b in history_buckets
            ]
            return FinancialStatsForecastResponse(
                buckets=result_buckets,
                highest_spending_bucket_index=int(history_response.financial_stats.highest_spending_bucket_index),
                highest_value=history_response.financial_stats.highest_value,
                predict=False
            )
        
        # ── 5. Build spending and budget series
        result_buckets = [
            CombinedForecastBucketDto(
                spending=b.spending,
                income=b.income,
                budget=b.budget,
                start_date=b.start_date,
                predicted=False,
                status=self.stats_service._determine_budget_status(b.spending, b.budget)[1]
            )
            for b in history_buckets
        ]

        # ── 6. Build Series for spending and budget separately
        dates = [b.start_date for b in history_buckets]
        spending_vals = [float(b.spending) for b in history_buckets]
        budget_vals = [float(b.budget)   for b in history_buckets]

        spending_series = pd.Series(spending_vals, index=pd.to_datetime(dates))
        budget_series = pd.Series(budget_vals, index=pd.to_datetime(dates))


        # ── 7. Validate signal 
        try:
            validate_spending_signal(spending_vals, budget_vals)
        except SparsityError as e:
            return CombinedForecastResponse(
                financial_stats_forecast=FinancialStatsForecastResponse(
                    buckets=[
                        CombinedForecastBucketDto(
                            spending=b.spending, income=b.income,
                            budget=b.budget, start_date=b.start_date, predicted=False
                        )
                        for b in history_buckets
                    ],
                    highest_spending_bucket_index=int(history_response.financial_stats.highest_spending_bucket_index),
                    highest_value=history_response.financial_stats.highest_value,
                    predict=False
                ),
                budget_status=history_response.budget_status,
                top_categories=history_response.top_categories
                )
        # ── 8. Clean spending anomalies (budget is deterministic — no IQR needed)
        cleaned_spending = self.anomaly.clean_series(spending_series)

        forecast_spending = self._fit_and_forecast(cleaned_spending, horizon, granularity)
        forecast_budget = self._fit_and_forecast(budget_series, horizon, granularity)

        future_dates = self._generate_future_dates(dates[-1], granularity, horizon)

        # ── 9. Append predicted buckets
        for val_s, val_b, fd in zip(forecast_spending, forecast_budget, future_dates):
            _, status = self.stats_service._determine_budget_status(
            Decimal(str(val_s)), Decimal(str(val_b))
            )
            result_buckets.append(CombinedForecastBucketDto(
                spending=Decimal(str(round(val_s, 2))),
                income=Decimal("0.00"),
                budget=Decimal(str(round(val_b, 2))),
                start_date=fd,
                predicted=True,
                status=status
            ))

        # ── 10. Recalculate highest_value across all buckets
        highest_value = max(
            max(b.spending, b.income + b.budget)
            for b in result_buckets
        )

        return CombinedForecastResponse(
            financial_stats_forecast= FinancialStatsForecastResponse(
                buckets=result_buckets,
                highest_spending_bucket_index=int(history_response.financial_stats.highest_spending_bucket_index),
                highest_value=highest_value,
                predict=True
            ),
            budget_status=history_response.budget_status,
            top_categories=history_response.top_categories
        )
 

    def _fit_and_forecast(
        self,
        series: pd.Series,
        horizon: int,
        granularity: Granularity
    ) -> np.ndarray:
        seasonality_period = GRANULARITY_SEASONALITY.get(granularity, 7)

        n = len(series)

        # Theta requires at least 2 × seasonality_period points
        # Reduce seasonality_period until the constraint is satisfied
        while seasonality_period > 1 and n < 2 * seasonality_period:
            seasonality_period -= 1

        # If still not enough even with seasonality_period=1, fall back to simple trend
        if n < 2:
            # Not enough data even for simplest model — return mean as flat forecast
            mean_val = float(series.mean()) if not series.empty else 0.0
            return np.clip(np.full(horizon, mean_val), a_min=0, a_max=None)
        
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
    
    def _subtract_buckets(self, from_date: datetime, granularity: Granularity, n: int) -> datetime:
        if granularity == Granularity.DAY:
            return from_date - timedelta(days=n)
        elif granularity == Granularity.WEEK:
            return from_date - timedelta(weeks=n)
        elif granularity == Granularity.MONTH:
            month = from_date.month - n
            year  = from_date.year
            while month <= 0:
                month += 12
                year  -= 1
            return from_date.replace(year=year, month=month, day=1)
        elif granularity == Granularity.YEAR:
            return from_date.replace(year=from_date.year - n)
        return from_date - timedelta(days=n)
    

    



   