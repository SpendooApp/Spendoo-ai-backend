from spendoo.core.database import Base


from sqlalchemy import Column, Numeric
from sqlalchemy.dialects.postgresql import UUID


import uuid


class SavingBalanceORM(Base):
    __tablename__ = "saving_balance"
    __table_args__ = {"schema": "saving_goals"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column("user_id", UUID(as_uuid=True), nullable=False)
    unassigned_amount = Column(
        "unassigned_amount", Numeric, nullable=False, default=0.0
    )
