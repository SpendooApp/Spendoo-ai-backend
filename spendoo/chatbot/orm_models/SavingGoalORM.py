from spendoo.core.database import Base


from sqlalchemy import Boolean, Column, DateTime, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID


import uuid


class SavingGoalORM(Base):
    __tablename__ = "saving_goals"
    __table_args__ = {"schema": "saving_goals"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column("user_id", UUID(as_uuid=True), nullable=False)
    goal_name = Column("goal_name", String, nullable=False)
    priority = Column(Integer, nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=False)
    target_amount = Column("target_amount", Numeric, nullable=False)
    is_completed = Column("is_completed", Boolean, nullable=False)
