from sqlalchemy import Column, Date, Float, String, ForeignKey
from app.db.session import Base

class MacroRaw(Base):
    __tablename__ = "macro_raw"

    date = Column(Date, primary_key=True)
    indicator = Column(String, ForeignKey("macro_indicators.ticker"), primary_key=True)
    value = Column(Float, nullable=False)
    source = Column(String, nullable=False, default="FRED")