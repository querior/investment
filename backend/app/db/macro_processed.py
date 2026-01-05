from sqlalchemy import Column, Date, Float, String
from app.db.session import Base

class MacroProcessed(Base):
    __tablename__ ="macro_processed"

    date = Column(Date, primary_key=True)
    indicator = Column(String, primary_key=True)

    value = Column(Float, nullable=False)
    z_score = Column(Float, nullable=False)

    source = Column(String, nullable=False, default="FRED")