from sqlalchemy import Column, Integer, String, Numeric, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class Master(Base):
    __tablename__ = "masters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    username = Column(String)
    category = Column(String)
    district = Column(String)
    rating = Column(Numeric)
    phone = Column(String)
    whatsapp_phone = Column(String)
    bio = Column(Text)
    photo_url = Column(Text)
    review_count = Column(Integer)
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    services = relationship("Service", back_populates="master")


class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    master_id = Column(Integer, ForeignKey("masters.id"))
    title = Column(String)
    description = Column(Text)
    price = Column(Numeric)
    duration_minutes = Column(Integer)
    is_active = Column(Boolean, default=True)

    master = relationship("Master", back_populates="services")
