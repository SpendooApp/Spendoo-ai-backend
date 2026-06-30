import pandas as pd
from decimal import Decimal

MIN_ACTIVE_SPENDING_BUCKETS = 3       # at least 3 buckets must have non-zero spending
MIN_TOTAL_SPENDING          = 100.0    # total spending across history must exceed this
MIN_ACTIVE_BUDGET_BUCKETS   = 0       # budget can be all zeros (user may not have set one)
                                       # so we don't reject on budget alone


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
    
def validate_spending_signal(spending_vals: list[float], budget_vals: list[float]) -> None:
    """
    Validates that history has enough real signal to forecast meaningfully.
    Raises SparsityError with a user-facing message if not.
    """
    total_spending = sum(spending_vals)
    active_spending = sum(1 for v in spending_vals if v > 0)
    total_buckets = len(spending_vals)

    # 1. Not enough total spending to be meaningful
    if total_spending < MIN_TOTAL_SPENDING:
        raise SparsityError(
            f"Total spending of {total_spending:.2f} across the selected period is too low "
            f"to generate a reliable forecast."
        )

    # 2. Too many zero-spending buckets — Theta can't learn from flatlines
    if active_spending < MIN_ACTIVE_SPENDING_BUCKETS:
        raise SparsityError(
            f"Only {active_spending}/{total_buckets} periods had any spending. "
            f"Need at least {MIN_ACTIVE_SPENDING_BUCKETS} active periods to forecast."
        )

    # 3. Spending is completely uniform (all values identical) — no pattern to learn
    if len(set(round(v, 2) for v in spending_vals)) == 1:
        raise SparsityError(
            "Spending is identical across all periods — no pattern available to forecast from."
        )

    # 4. Budget-specific: warn if budget is all zeros but don't hard-reject
    # (user may not have set a budget for this category — that's valid)
    total_budget = sum(budget_vals)
    if total_budget == 0:
        raise SparsityError(
            "No budget has been set for this period. "
            "Set a budget first to enable budget forecasting."
        )
    
    # Minimum points for any Theta model (seasonality_period=1 needs at least 2)
    if len(spending_vals) < 2:
        raise SparsityError(
            f"Only {len(spending_vals)} history bucket(s) found. "
            f"Need at least 2 to forecast."
        )