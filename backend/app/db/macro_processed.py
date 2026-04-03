from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Date, String, Float
from app.db.session import Base
import datetime

class MacroProcessed(Base):
    __tablename__ = "macro_processed"

    date: Mapped[datetime.date] = mapped_column(Date, primary_key=True)
    indicator: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    z_score: Mapped[float] = mapped_column(Float, nullable=False)
    z_score_ema: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String, nullable=False, default="FRED")