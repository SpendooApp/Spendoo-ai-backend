from sqlalchemy import Column, String, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID
import uuid
from spendoo.core.database import Base

class TransactionORM(Base):
    __tablename__ = "transactions"
    __table_args__ = {"schema": "spending"}

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    amount           = Column(Numeric, nullable=False)
    transaction_date = Column(DateTime, nullable=False)
    user_id          = Column(UUID(as_uuid=True), nullable=False)
    category_id      = Column(UUID(as_uuid=True), nullable=True)
    title            = Column(String, nullable=True)
    note             = Column(String, nullable=True)