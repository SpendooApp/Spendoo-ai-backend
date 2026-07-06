from sqlalchemy import Column, String, Numeric, DateTime, Boolean, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
import uuid
from spendoo.core.database import Base

class TransactionORM(Base):
    __tablename__ = "transactions"
    __table_args__ = {"schema": "spending"}

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    amount           = Column(Numeric, nullable=False)
    transaction_date = Column(DateTime(timezone=True), nullable=False)
    user_id          = Column(UUID(as_uuid=True), nullable=False)
    category_id      = Column(UUID(as_uuid=True), nullable=True)
    title            = Column(String, nullable=True)
    note             = Column(String, nullable=True)

class BudgetORM(Base):
    __tablename__ = "budgets"
    __table_args__ = {"schema": "spending"}

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_id = Column(UUID(as_uuid=True), ForeignKey("spending.categories.id"), nullable=False)
    amount      = Column(Numeric, nullable=False)
    period      = Column(Integer, nullable=False)
    start_date  = Column(DateTime(timezone=True), nullable=False)
    end_date    = Column(DateTime(timezone=True), nullable=False)
    is_active   = Column(Boolean, nullable=False, default=True)