from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class InstrumentConfig(Base):
    __tablename__ = "instrument_configs"

    ticker: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    dividend_yield: Mapped[float] = mapped_column(Float, nullable=False)
    iv_proxy: Mapped[str] = mapped_column(String(30), nullable=False)
    iv_alpha: Mapped[float] = mapped_column(Float, nullable=False)
    contract_multiplier: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    settlement: Mapped[str] = mapped_column(String(20), nullable=False, default="physical")
    iv_min: Mapped[float] = mapped_column(Float, nullable=False, default=0.10)
    iv_max: Mapped[float] = mapped_column(Float, nullable=False, default=0.80)
    commission_per_contract: Mapped[float] = mapped_column(Float, nullable=False, default=0.65)
    min_commission: Mapped[float] = mapped_column(Float, nullable=False, default=1.00)
    bid_ask_spread_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.02)
