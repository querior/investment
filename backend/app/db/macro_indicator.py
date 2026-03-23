import enum
from sqlalchemy import Column, Integer, String, Boolean, Enum as SAEnum
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

    id = Column(Integer, primary_key=True)
    ticker = Column(String, unique=True, nullable=False)
    source = Column(SAEnum(IndicatorSource, name="indicator_source"), nullable=False)
    description = Column(String, nullable=False)
    frequency = Column(SAEnum(IndicatorFrequency, name="indicator_frequency"), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
