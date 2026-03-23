from sqlalchemy import Column, Integer, Float, ForeignKey, UniqueConstraint
from app.db.session import Base


class CompositeScoreWeight(Base):
    __tablename__ = "composite_score_weights"

    id = Column(Integer, primary_key=True)
    composite_score_id = Column(Integer, ForeignKey("composite_scores.id"), nullable=False)
    pillar_id = Column(Integer, ForeignKey("pillars.id"), nullable=False)
    weight = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("composite_score_id", "pillar_id", name="uq_score_pillar"),
    )
