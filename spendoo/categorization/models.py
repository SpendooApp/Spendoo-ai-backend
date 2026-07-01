from pydantic import BaseModel
from sqlalchemy import Column, Boolean, Integer, String
from sqlalchemy.dialects.postgresql import UUID
import uuid
from spendoo.core.database import Base


class CategoryORM(Base):
    __tablename__ = "categories"
    __table_args__ = {"schema": "spending"}

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    category_name = Column(String, nullable=False)
    category_icon = Column(String, nullable=True)
    is_deleted = Column(Boolean, default=False)
    left_over_options = Column(String, nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    priority = Column(Integer, nullable=False, default=1)

class CategorySchema(BaseModel):
    id: str
    category_name: str
    category_icon: str | None
    is_deleted: bool
    left_over_options: str | None
    user_id: str

    class Config:
        from_attributes = True

class CategorizationRequest(BaseModel):
    text: str
    user_id: uuid.UUID


