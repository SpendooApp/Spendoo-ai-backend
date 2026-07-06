from spendoo.core.database import Base


from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID


import uuid


class UserORM(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "identity"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column("full_name", String, nullable=False)
    email = Column(String, nullable=False)
    gender = Column(String, nullable=False)
    birth_date = Column("birth_date", DateTime(timezone=True), nullable=False)
    is_verified = Column("is_verified", Boolean, nullable=False)
    created_at = Column("created_at", DateTime(timezone=True), nullable=False)
    image_url = Column("image_url", String, nullable=True)
