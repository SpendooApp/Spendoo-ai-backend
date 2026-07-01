from spendoo.core.database import Base


from sqlalchemy import Column, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID


import uuid


class UserAchievementORM(Base):
    __tablename__ = "user_achievements"
    __table_args__ = {"schema": "saving_goals"}
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column("user_id", UUID(as_uuid=True), nullable=False)
    achievement_id = Column(
        "achievement_id",
        UUID(as_uuid=True),
        ForeignKey("saving_goals.achievements.id"),
        nullable=False,
    )
    unlocked_at = Column("unlocked_at", DateTime, nullable=False)
