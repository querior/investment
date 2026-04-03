import enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, Enum as SAEnum
from app.db.session import Base


class IndicatorSource(str, enum.Enum):
    FRED = "FRED"


class IndicatorFrequency(str, enum.Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"


class MacroIndicator(Base):
    __tablename__ = "macro_indicators"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticker: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    source: Mapped[IndicatorSource] = mapped_column(SAEnum(IndicatorSource, name="indicator_source"), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    frequency: Mapped[IndicatorFrequency] = mapped_column(SAEnum(IndicatorFrequency, name="indicator_frequency"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)