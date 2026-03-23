from sqlalchemy import Column, Integer, Float, ForeignKey, UniqueConstraint
from app.db.session import Base


class PillarComponent(Base):
    __tablename__ = "pillar_components"

    id = Column(Integer, primary_key=True)
    pillar_id = Column(Integer, ForeignKey("pillars.id"), nullable=False)
    processed_indicator_id = Column(Integer, ForeignKey("processed_indicators.id"), nullable=False)
    weight = Column(Float, nullable=False, default=1.0)
    display_order = Column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("pillar_id", "processed_indicator_id", name="uq_pillar_component"),
    )
