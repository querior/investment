from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Date, Float, String, Integer
from app.db.session import Base
import datetime

class MacroRegime(Base):
  __tablename__ = "macro_regimes"

  date: Mapped[datetime.date] = mapped_column(Date, primary_key=True)
  pillar: Mapped[str] = mapped_column(String, primary_key=True)
  score: Mapped[float] = mapped_column(Float)
  score_ema: Mapped[float | None] = mapped_column(Float, nullable=True)
  regime: Mapped[str] = mapped_column(String)
  counter: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
  pending: Mapped[str | None] = mapped_column(String, nullable=True)