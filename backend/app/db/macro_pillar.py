from sqlalchemy import Column, Date, Float, String
from app.db.session import Base

class MacroPillar(Base):
  __tablename__ = "macro_pillars"
  
  date = Column(Date, primary_key=True)
  pillar = Column(String, primary_key=True)
  score = Column(Float, nullable=False)