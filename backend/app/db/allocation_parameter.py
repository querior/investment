from sqlalchemy import Column, Integer, String, Float
from app.db.session import Base


class AllocationParameter(Base):
    __tablename__ = "allocation_parameters"

    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, nullable=False)
    value = Column(Float, nullable=False)
    description = Column(String, nullable=False)
