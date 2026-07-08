from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.post import _utcnow_aware


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(255), nullable=False)
    text = Column(Text, nullable=False)
    type = Column(String(50), nullable=True)
    unread = Column(Boolean, nullable=True, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow_aware, nullable=True)

    user = relationship("User")
