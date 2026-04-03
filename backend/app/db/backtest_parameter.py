from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, Float, ForeignKey
from app.db.session import Base


class BacktestParameter(Base):
    __tablename__ = "backtest_parameters"

    id          : Mapped[int]   = mapped_column(Integer, primary_key=True)
    backtest_id : Mapped[int | None] = mapped_column(Integer, ForeignKey("backtests.id", ondelete="CASCADE"), nullable=True)
    key         : Mapped[str]   = mapped_column(String)
    value       : Mapped[float] = mapped_column(Float)
    description : Mapped[str]   = mapped_column(String)