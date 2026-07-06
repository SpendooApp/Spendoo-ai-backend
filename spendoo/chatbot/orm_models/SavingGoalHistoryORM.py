from spendoo.core.database import Base


from sqlalchemy import Column, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID


import uuid


class SavingGoalHistoryORM(Base):
    __tablename__ = "goals_history"
    __table_args__ = {"schema": "saving_goals"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    amount = Column(Numeric, nullable=False)
    created_at = Column("created_at", DateTime(timezone=True), nullable=False)
    goal_id = Column(
        "goal_id",
        UUID(as_uuid=True),
        ForeignKey("saving_goals.saving_goals.id"),
        nullable=False,
    )
