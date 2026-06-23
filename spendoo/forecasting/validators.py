import pandas as pd

class SparsityError(Exception):
    """Raised when user data is too sparse to forecast reliably."""
    pass

def validate_forecast_ratio(history_count: int, horizon: int) -> None:
    """
    Reject if the forecast horizon is disproportionately large relative to history.
    Rule: you need at least 2x as many history buckets as you want to predict forward.
    e.g. predicting 5 weeks forward requires at least 10 weeks of history.
    """
    if history_count == 0:
        raise SparsityError("No historical data available to forecast from.")

    ratio = history_count / horizon
    if ratio < 2.0:
        raise SparsityError(
            f"Insufficient history: {history_count} buckets of history to predict "
            f"{horizon} buckets forward (ratio {ratio:.1f}x). "
            f"Need at least 2x history — either reduce the forecast horizon or "
            f"provide a longer history window."
        )