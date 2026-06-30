from sqlalchemy.orm import Session
from spendoo.core.models import TransactionORM, BudgetORM
from spendoo.categorization.models import CategoryORM
import uuid
from datetime import datetime

class StatisticsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_transactions_in_range(self, user_id: uuid.UUID, start_date: datetime, end_date: datetime, category_id: uuid.UUID = None):
        query = (
            self.db.query(TransactionORM)
            .filter(
                TransactionORM.user_id == user_id,
                TransactionORM.transaction_date >= start_date,
                TransactionORM.transaction_date < end_date
            )
        )

        if category_id is not None:
            query = query.filter(TransactionORM.category_id == category_id)

        return query.all()

    def get_overlapping_budgets(self, user_id: uuid.UUID, start_date: datetime, end_date: datetime, category_id: uuid.UUID = None):
        query = (
            self.db.query(BudgetORM)
            .join(CategoryORM, BudgetORM.category_id == CategoryORM.id)
            .filter(
                CategoryORM.user_id == user_id,
                BudgetORM.start_date < end_date,
                BudgetORM.end_date > start_date
            )
        )

        if category_id is not None:
            query = query.filter(BudgetORM.category_id == category_id)

        return query.all()

    def get_user_categories(self, user_id: uuid.UUID):
        return (
            self.db.query(CategoryORM)
            .filter(
                CategoryORM.user_id == user_id,
                CategoryORM.is_deleted == False
            )
            .all()
        )

