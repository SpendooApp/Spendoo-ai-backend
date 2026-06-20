from sqlalchemy.orm import Session
from spendoo.core.models import TransactionORM, BudgetORM
from spendoo.categorization.models import CategoryORM
import uuid
from datetime import datetime

class StatisticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_transactions_in_range(self, user_id: uuid.UUID, start_date: datetime, end_date: datetime):
        from sqlalchemy import or_
        return (
            self.db.query(TransactionORM)
            .filter(
                TransactionORM.user_id == user_id,
                TransactionORM.transaction_date >= start_date,
                TransactionORM.transaction_date < end_date,
                or_(TransactionORM.amount >= 0, TransactionORM.category_id.isnot(None))
            )
            .all()
        )

    def get_overlapping_budgets(self, user_id: uuid.UUID, start_date: datetime, end_date: datetime):
        return (
            self.db.query(BudgetORM)
            .join(CategoryORM, BudgetORM.category_id == CategoryORM.id)
            .filter(
                CategoryORM.user_id == user_id,
                BudgetORM.start_date < end_date,
                BudgetORM.end_date > start_date
            )
            .all()
        )
