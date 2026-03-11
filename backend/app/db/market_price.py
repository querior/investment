from sqlalchemy import Column, String, Date, Float
from app.db.session import Base

class MarketPrice(Base):
  __tablename__ = "market_prices"

  symbol = Column(String, primary_key=True)  # es: "SPY", "IEF", "DBC", "BIL"
  date = Column(Date, primary_key=True)
  open = Column(Float, nullable=False)
  high = Column(Float, nullable=False)
  low = Column(Float, nullable=False)
  close = Column(Float, nullable=False)
  volume = Column(Float, nullable=False)
  source = Column(String, nullable=False)
