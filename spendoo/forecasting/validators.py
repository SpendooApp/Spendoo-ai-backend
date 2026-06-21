import pandas as pd

# Thresholds
MIN_ACTIVE_DAYS_RATIO = 0.7    # at least 70% of days must have spending
MIN_TOTAL_SPENDING    = 500.0   # total must be more than 500 EGP (not a ghost account)
MIN_UNIQUE_DAYS       = 20      # must have spent on at least 20 distinct days

class SparsityError(Exception):
    """Raised when user data is too sparse to forecast reliably."""
    pass

def validate_spending_series(series: pd.Series) -> None:
    """
    Raises SparsityError with a descriptive message if the series
    is too sparse or empty to produce a meaningful forecast.
    """
    total_days   = len(series)
    active_days  = int((series > 0).sum())
    total_spent  = float(series.sum())
    active_ratio = active_days / total_days if total_days > 0 else 0

    if total_days == 0 or total_spent == 0:
        raise SparsityError(
            "No spending data found for this period."
        )

    if active_days < MIN_UNIQUE_DAYS:
        raise SparsityError(
            f"Only {active_days} days with spending in the last {total_days} days. "
            f"Need at least {MIN_UNIQUE_DAYS} active days to forecast."
        )

    if active_ratio < MIN_ACTIVE_DAYS_RATIO:
        raise SparsityError(
            f"{active_days}/{total_days} days have spending ({active_ratio:.0%}). "
            f"Need at least {MIN_ACTIVE_DAYS_RATIO:.0%} active days to forecast reliably."
        )

    if total_spent < MIN_TOTAL_SPENDING:
        raise SparsityError(
            f"Total spending of {total_spent:.2f} EGP is too low to forecast meaningfully."
        )