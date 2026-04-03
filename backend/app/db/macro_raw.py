from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Date, Float, String, ForeignKey
from app.db.session import Base
import datetime

class MacroRaw(Base):
    __tablename__ = "macro_raw"

    date: Mapped[datetime.date] = mapped_column(Date, primary_key=True)
    indicator: Mapped[str] = mapped_column(String, ForeignKey("macro_indicators.ticker"), primary_key=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False, default="FRED")