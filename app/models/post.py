from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from app.db.session import Base


def _utcnow_aware() -> datetime:
    return datetime.now(timezone.utc)


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    # Despite the name, this pre-existing column is a FK to users.id (not
    # masters.id) — it was modeled back when "master" meant a User with
    # role='master', before masters became their own table.
    master_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    image_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow_aware, nullable=True)

    owner = relationship("User")
    service = relationship("Service")


class PostLike(Base):
    __tablename__ = "post_likes"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)


class PostSave(Base):
    __tablename__ = "post_saves"

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
