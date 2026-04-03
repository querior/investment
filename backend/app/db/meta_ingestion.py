from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Date, DateTime
from sqlalchemy.sql import func
from app.db.session import Base
import datetime

class IngestionState(Base):
    __tablename__ = "ingestion_state"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    last_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)