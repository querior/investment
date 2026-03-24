from sqlalchemy import Column, Integer, ForeignKey, Date, String, Float
from app.db.session import Base


class BacktestWeight(Base):
    __tablename__ = "backtest_weights"

    run_id = Column(Integer, ForeignKey("backtest_runs.id", ondelete="CASCADE"), primary_key=True)
    date = Column(Date, primary_key=True)
    asset = Column(String, primary_key=True)

    weight = Column(Float, nullable=False)
    macro_score = Column(Float, nullable=True)
    pillar_scores = Column(String, nullable=True)  # JSON: {"Growth": 0.45, ...}
