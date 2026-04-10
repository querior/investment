from sqlalchemy import Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


class BacktestRunParameter(Base):
    __tablename__ = "backtest_run_parameters"

    id     : Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id : Mapped[int] = mapped_column(Integer, ForeignKey("backtest_runs.id", ondelete="CASCADE"), nullable=False)
    key    : Mapped[str] = mapped_column(String, nullable=False)
    value  : Mapped[str] = mapped_column(String, nullable=False)
    unit   : Mapped[str] = mapped_column(String, nullable=False, default="value")

    __table_args__ = (UniqueConstraint("run_id", "key"),)
