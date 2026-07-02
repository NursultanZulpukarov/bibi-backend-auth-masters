from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.time import utcnow
from app.db.session import Base


class Master(Base):
    __tablename__ = "masters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, unique=True)
    name = Column(String(100), nullable=False)
    username = Column(String(50), nullable=False, unique=True, index=True)
    category = Column(String(50), nullable=False)
    district = Column(String(100), nullable=True)
    rating = Column(Numeric(3, 2), nullable=True)
    phone = Column(String(20), nullable=True)
    whatsapp_phone = Column(String(20), nullable=True)
    bio = Column(Text, nullable=True)
    photo_url = Column(Text, nullable=True)
    review_count = Column(Integer, nullable=True, default=0)
    is_verified = Column(Boolean, nullable=True, default=False)
    is_active = Column(Boolean, nullable=True, default=True)

    owner = relationship("User", back_populates="master_profile")
    services = relationship("Service", back_populates="master", cascade="all, delete-orphan")


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    master_id = Column(Integer, ForeignKey("masters.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    duration = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=True, default=True)
    category = Column(String(100), nullable=True)
    image_url = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=True)

    master = relationship("Master", back_populates="services")
