from sqlalchemy import Column, Integer, String, Float, ForeignKey
from app.db.session import Base


class RegimeThreshold(Base):
    __tablename__ = "regime_thresholds"

    id = Column(Integer, primary_key=True)
    composite_score_id = Column(Integer, ForeignKey("composite_scores.id"), nullable=False)
    name = Column(String, nullable=False)
    threshold_min = Column(Float, nullable=True)  # NULL = nessun lower bound (regime più basso)
    display_order = Column(Integer, nullable=False)
