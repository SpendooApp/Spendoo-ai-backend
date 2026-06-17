from sqlalchemy.orm import Session
from spendoo.core.models import TransactionORM
from datetime import date, timedelta
import pandas as pd

class AnomalyRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_daily_spending(self, user_id, days: int) -> pd.Series:
        """
        Returns a daily spending Series for the last `days` days,
        with 0 for days with no transactions.
        """
        end_date   = date.today()
        start_date = end_date - timedelta(days=days - 1)

        rows = (
            self.db.query(TransactionORM.transaction_date, TransactionORM.amount)
            .filter(
                TransactionORM.user_id == user_id,
                TransactionORM.transaction_date >= start_date,
                TransactionORM.transaction_date <= end_date,
            )
            .all()
        )

        df = pd.DataFrame(rows, columns=["transaction_date", "amount"])

        if df.empty:
            daily = pd.Series(dtype=float)
        else:
            df["transaction_date"] = pd.to_datetime(df["transaction_date"]).dt.normalize()
            df["amount"] = df["amount"].astype(float)
            daily = df.groupby("transaction_date")["amount"].sum()

        # Fill the full date range with 0 for days with no spending
        full_range = pd.date_range(start=start_date, end=end_date, freq="D")
        daily = daily.reindex(full_range, fill_value=0.0)
        daily.index.name = "ds"

        return daily