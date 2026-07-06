from spendoo.core.database import Base


from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID


import uuid


class NotificationORM(Base):
    __tablename__ = "notifications"
    __table_args__ = {"schema": "notification"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column("user_id", UUID(as_uuid=True), nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    type = Column(String, nullable=False)
    is_read = Column("is_read", Boolean, nullable=False)
    sent_at = Column("sent_at", DateTime(timezone=True), nullable=False)
