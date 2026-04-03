from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Date, Float, ForeignKey
from app.db.session import Base
import datetime

class MarketPrice(Base):
  __tablename__ = "market_prices"

  symbol: Mapped[str] = mapped_column(String, ForeignKey("market_symbols.symbol"), primary_key=True)
  date: Mapped[datetime.date] = mapped_column(Date, primary_key=True)
  open: Mapped[float] = mapped_column(Float, nullable=False)
  high: Mapped[float] = mapped_column(Float, nullable=False)
  low: Mapped[float] = mapped_column(Float, nullable=False)
  close: Mapped[float] = mapped_column(Float, nullable=False)
  volume: Mapped[float] = mapped_column(Float, nullable=False)
  source: Mapped[str] = mapped_column(String, nullable=False)