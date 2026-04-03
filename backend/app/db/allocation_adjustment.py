from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from app.db.session import Base

class AllocationAdjustment(Base):
  __tablename__ = "allocation_adjustments"

  id     : Mapped[int]   = mapped_column(Integer, primary_key=True)
  pillar : Mapped[str]   = mapped_column(String, nullable=False)
  regime : Mapped[str]   = mapped_column(String, nullable=False)  # expansion / neutral / contraction
  asset  : Mapped[str]   = mapped_column(String, nullable=False)  # Equity / Bond / Commodities / Cash
  delta  : Mapped[float] = mapped_column(Float, nullable=False)