from .repository import AnomalyRepository
from .models import AnomalyResponse
import pandas as pd


class AnomalyService:
    def __init__(self, db):
        self.repo = AnomalyRepository(db)

    def detect(self, user_id, days: int = 30) -> AnomalyResponse:
        y = self.repo.get_daily_spending(user_id, days)

        if y.empty:
            return self._empty_response(y, reason="No transaction data found")

        zero_days = int((y == 0).sum())
        zero_ratio = zero_days / len(y)

        # Threshold: if more than 70% of days have no spending, data is too sparse
        if zero_ratio > 0.3:
            return self._empty_response(
                y,
                reason=f"Insufficient data: {zero_days}/{len(y)} days have no spending"
            )
    
        # ── IQR (Tukey's fences) ─────────────────────────────────────────────
        Q1 = y.quantile(0.25)
        Q3 = y.quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = max(0.0, Q1 - 1.5 * IQR)
        upper_bound = Q3 + 1.5 * IQR

        is_anomaly = (y < lower_bound) | (y > upper_bound)

        # ── Clean: replace anomalies with rolling median ────────────────────
        rolling_median = y.rolling(5, min_periods=1).median()
        cleaned = y.copy()
        cleaned[is_anomaly] = rolling_median[is_anomaly]

        return AnomalyResponse(
            dates=y.index.strftime("%Y-%m-%d").tolist(),
            original_values=y.tolist(),
            cleaned_values=cleaned.tolist(),
            is_anomaly=is_anomaly.tolist(),
            anomaly_dates=y.index[is_anomaly].strftime("%Y-%m-%d").tolist(),
            anomaly_count=int(is_anomaly.sum()),
            lower_bound=float(lower_bound),
            upper_bound=float(upper_bound),
        )
    
    def _empty_response(self, y: pd.Series, reason: str) -> AnomalyResponse:
        return AnomalyResponse(
            dates=y.index.strftime("%Y-%m-%d").tolist() if not y.empty else [],
            original_values=y.tolist() if not y.empty else [],
            cleaned_values=y.tolist() if not y.empty else [],
            is_anomaly=[False] * len(y),
            anomaly_dates=[],
            anomaly_count=0,
            lower_bound=0.0,
            upper_bound=0.0,
            message=reason,   
        )
    
    def clean_series(self, series: pd.Series) -> pd.Series:
        """
        NEW: Pure IQR cleaning on an already-prepared Series.
        Used by ForecastService on bucketed (day/week/month/year) data,
        not just raw daily transactions.
        """
        if series.empty or len(series) < 4:
            return series  # not enough data for quartiles to be meaningful

        Q1 = series.quantile(0.25)
        Q3 = series.quantile(0.75)
        IQR = Q3 - Q1

        lower_bound = max(0.0, Q1 - 1.5 * IQR)
        upper_bound = Q3 + 1.5 * IQR

        is_anomaly = (series < lower_bound) | (series > upper_bound)
        rolling_median = series.rolling(5, min_periods=1).median()

        cleaned = series.copy()
        cleaned[is_anomaly] = rolling_median[is_anomaly]
        return cleaned