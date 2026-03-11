from sqlalchemy import Column, String, Date, DateTime
from sqlalchemy.sql import func
from app.db.session import Base

class IngestionState(Base):
    __tablename__ = "ingestion_state"

    key = Column(String, primary_key=True)      # es: "FRED:INDPRO" o "MK:SPY"
    last_date = Column(Date, nullable=True)     # ultima data salvata
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

