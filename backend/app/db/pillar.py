from sqlalchemy import Column, Integer, String, Boolean
from app.db.session import Base


class Pillar(Base):
    __tablename__ = "pillars"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=False)
    display_order = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
