from spendoo.core.database import Base


from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID


import uuid


class ScheduledPaymentORM(Base):
    __tablename__ = "scheduled_payments"
    __table_args__ = {"schema": "spending"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column("user_id", UUID(as_uuid=True), nullable=False)
    title = Column(String, nullable=False)
    amount = Column(Numeric, nullable=False)
    start_date = Column("start_date", DateTime(timezone=True), nullable=False)
    next_due_date = Column("next_due_date", DateTime(timezone=True), nullable=False)
    frequency = Column(Integer, nullable=False)
    category_id = Column(
        "category_id",
        UUID(as_uuid=True),
        ForeignKey("spending.categories.id"),
        nullable=False,
    )
