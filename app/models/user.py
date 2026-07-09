from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.time import utcnow
from app.db.session import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    phone = Column(String(20), unique=True, nullable=True, index=True)
    password_hash = Column(Text, nullable=False)
    name = Column(String(100), nullable=True, default="")
    avatar_url = Column(Text, nullable=True)
    role = Column(String(20), nullable=False, default="client")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=utcnow, nullable=True)

    master_profile = relationship("Master", back_populates="owner", uselist=False)
