from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import uuid
from datetime import datetime
from spendoo.chatbot.orm_models.AchievementORM import AchievementORM
from spendoo.chatbot.orm_models.CategoryORM import CategoryORM
from spendoo.chatbot.orm_models.NotificationORM import NotificationORM
from spendoo.chatbot.orm_models.SavingBalanceORM import SavingBalanceORM
from spendoo.chatbot.orm_models.SavingGoalORM import SavingGoalORM
from spendoo.chatbot.orm_models.ScheduledPaymentORM import ScheduledPaymentORM
from spendoo.chatbot.orm_models.UserAchievementORM import UserAchievementORM
from spendoo.chatbot.orm_models.UserORM import UserORM
from spendoo.chatbot.orm_models.SavingGoalHistoryORM import SavingGoalHistoryORM
from spendoo.core.models import TransactionORM, BudgetORM


def get_user_info(db: Session, user_id: uuid.UUID):
    return db.query(UserORM).filter(UserORM.id == user_id).first()


def get_transactions(
    db: Session, user_id: uuid.UUID, limit: int = 50, start_date=None, end_date=None
):
    query = db.query(TransactionORM).filter(TransactionORM.user_id == user_id)
    if start_date:
        query = query.filter(TransactionORM.transaction_date >= start_date)
    if end_date:
        query = query.filter(TransactionORM.transaction_date <= end_date)
    query = query.filter(
        ~((TransactionORM.amount < 0) & (TransactionORM.category_id.is_(None)))
    )
    return query.order_by(TransactionORM.transaction_date.desc()).limit(limit).all()


def get_categories(db: Session, user_id: uuid.UUID):
    return (
        db.query(CategoryORM)
        .filter(CategoryORM.user_id == user_id, CategoryORM.is_deleted == False)
        .order_by(CategoryORM.priority)
        .all()
    )


def get_budgets(db: Session, user_id: uuid.UUID):
    return (
        db.query(BudgetORM)
        .join(CategoryORM, BudgetORM.category_id == CategoryORM.id)
        .filter(CategoryORM.user_id == user_id, BudgetORM.is_active == True)
        .all()
    )


def get_scheduled_payments(db: Session, user_id: uuid.UUID):
    return (
        db.query(ScheduledPaymentORM)
        .filter(ScheduledPaymentORM.user_id == user_id)
        .all()
    )


def get_saving_goals(db: Session, user_id: uuid.UUID):
    return db.query(SavingGoalORM).filter(SavingGoalORM.user_id == user_id).all()


def get_achievements(db: Session, user_id: uuid.UUID):
    return (
        db.query(UserAchievementORM, AchievementORM)
        .join(AchievementORM, UserAchievementORM.achievement_id == AchievementORM.id)
        .filter(UserAchievementORM.user_id == user_id)
        .all()
    )


def get_notifications(db: Session, user_id: uuid.UUID, limit: int = 20):
    return (
        db.query(NotificationORM)
        .filter(NotificationORM.user_id == user_id)
        .order_by(NotificationORM.sent_at.desc())
        .limit(limit)
        .all()
    )


def get_balance_summary(db: Session, user_id: uuid.UUID):
    budgets = (
        db.query(func.coalesce(func.sum(BudgetORM.amount), 0))
        .join(CategoryORM, BudgetORM.category_id == CategoryORM.id)
        .filter(
            CategoryORM.user_id == user_id,
            CategoryORM.is_deleted == False,
            BudgetORM.is_active == True,
        )
        .scalar()
    )

    income = (
        db.query(func.coalesce(func.sum(TransactionORM.amount), 0))
        .filter(TransactionORM.user_id == user_id, TransactionORM.category_id.is_(None))
        .scalar()
    )

    expenses = (
        db.query(func.coalesce(func.sum(TransactionORM.amount), 0))
        .filter(
            TransactionORM.user_id == user_id,
            TransactionORM.amount < 0,
            TransactionORM.category_id.is_not(None),
        )
        .scalar()
    )

    real_income = budgets + income
    total_balance = real_income + expenses
    return {
        "total_balance": total_balance,
        "income": real_income,
        "expenses": -expenses,
    }


def get_categories_summary(db: Session, user_id: uuid.UUID):
    total_budget = (
        db.query(func.coalesce(func.sum(BudgetORM.amount), 0))
        .join(CategoryORM, BudgetORM.category_id == CategoryORM.id)
        .filter(
            CategoryORM.user_id == user_id,
            CategoryORM.is_deleted == False,
            BudgetORM.is_active == True,
        )
        .scalar()
    )

    # Total spent: sum amount of transactions mapped to categories where transaction is within active budget dates
    total_spent = (
        db.query(func.coalesce(func.sum(TransactionORM.amount), 0))
        .join(CategoryORM, TransactionORM.category_id == CategoryORM.id)
        .join(BudgetORM, BudgetORM.category_id == CategoryORM.id)
        .filter(
            CategoryORM.user_id == user_id,
            CategoryORM.is_deleted == False,
            BudgetORM.is_active == True,
            TransactionORM.amount < 0,
            TransactionORM.transaction_date >= BudgetORM.start_date,
            TransactionORM.transaction_date <= BudgetORM.end_date,
        )
        .scalar()
    )

    added_income = (
        db.query(func.coalesce(func.sum(TransactionORM.amount), 0))
        .filter(TransactionORM.user_id == user_id, TransactionORM.category_id.is_(None))
        .scalar()
    )

    return {
        "total_budget": total_budget,
        "total_spent": total_spent,
        "added_income": added_income,
    }


def get_scheduled_payments_summary(db: Session, user_id: uuid.UUID):
    total_amount = (
        db.query(func.coalesce(func.sum(ScheduledPaymentORM.amount), 0))
        .filter(ScheduledPaymentORM.user_id == user_id)
        .scalar()
    )

    now = datetime.now()
    upcoming_count = (
        db.query(func.count(ScheduledPaymentORM.id))
        .filter(
            ScheduledPaymentORM.user_id == user_id,
            ScheduledPaymentORM.next_due_date > now,
        )
        .scalar()
    )

    return {"total_scheduled_amount": total_amount, "upcoming_count": upcoming_count}


def get_saving_goals_summary(db: Session, user_id: uuid.UUID):
    total_saved = (
        db.query(func.coalesce(func.sum(SavingGoalHistoryORM.amount), 0))
        .join(SavingGoalORM, SavingGoalHistoryORM.goal_id == SavingGoalORM.id)
        .filter(SavingGoalORM.user_id == user_id)
        .scalar()
    )

    total_target = (
        db.query(func.coalesce(func.sum(SavingGoalORM.target_amount), 0))
        .filter(SavingGoalORM.user_id == user_id)
        .scalar()
    )

    unassigned_amount = (
        db.query(func.coalesce(func.sum(SavingBalanceORM.unassigned_amount), 0))
        .filter(SavingBalanceORM.user_id == user_id)
        .scalar()
    )

    return {
        "total_saved": total_saved,
        "total_target": total_target,
        "unassigned_amount": unassigned_amount,
    }


def get_top_spending_categories(db: Session, user_id: uuid.UUID, limit: int = 5):
    res = (
        db.query(
            CategoryORM.id,
            CategoryORM.category_name,
            CategoryORM.category_icon,
            func.sum(TransactionORM.amount).label("spent"),
        )
        .join(TransactionORM, TransactionORM.category_id == CategoryORM.id)
        .filter(TransactionORM.user_id == user_id, TransactionORM.amount < 0)
        .group_by(CategoryORM.id, CategoryORM.category_name, CategoryORM.category_icon)
        .order_by(func.abs(func.sum(TransactionORM.amount)).desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "category_id": str(r.id),
            "category_name": r.category_name,
            "category_icon": r.category_icon,
            "total_spent": float(r.spent),
        }
        for r in res
    ]


def get_top_frequency_items(db: Session, user_id: uuid.UUID, limit: int = 5):
    res = (
        db.query(
            TransactionORM.title,
            func.count(TransactionORM.id).label("freq"),
            func.sum(TransactionORM.amount).label("spent"),
            CategoryORM.id.label("category_id"),
            CategoryORM.category_icon,
        )
        .join(CategoryORM, TransactionORM.category_id == CategoryORM.id)
        .filter(
            TransactionORM.user_id == user_id,
            TransactionORM.amount < 0,
            TransactionORM.category_id.is_not(None),
        )
        .group_by(TransactionORM.title, CategoryORM.id, CategoryORM.category_icon)
        .order_by(
            func.count(TransactionORM.id).desc(),
            func.abs(func.sum(TransactionORM.amount)).desc(),
        )
        .limit(limit)
        .all()
    )

    return [
        {
            "title": r.title,
            "frequency": r.freq,
            "total_spent": float(r.spent),
            "category_id": str(r.category_id) if r.category_id else None,
            "category_icon": r.category_icon,
        }
        for r in res
    ]
