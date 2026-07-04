from spendoo.core.database import Base


from sqlalchemy import Column, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID


import uuid


class AchievementORM(Base):
    __tablename__ = "achievements"
    __table_args__ = {"schema": "saving_goals"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, nullable=False)
    target_value = Column("target_value", Numeric, nullable=False)
    level = Column(Integer, nullable=False)
    title_en = Column("title_en", String, nullable=False)
    title_ar = Column("title_ar", String, nullable=False)
    description_en = Column("description_en", String, nullable=False)
    description_ar = Column("description_ar", String, nullable=False)
