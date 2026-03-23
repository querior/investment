from sqlalchemy import Column, Integer, String, Boolean
from app.db.session import Base


class CompositeScore(Base):
    __tablename__ = "composite_scores"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    display_order = Column(Integer, nullable=False, default=0)
