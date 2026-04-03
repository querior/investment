from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Float, ForeignKey, UniqueConstraint, Integer
from app.db.session import Base


class PillarComponent(Base):
    __tablename__ = "pillar_components"

    id: Mapped[int] = mapped_column(primary_key=True)
    pillar_id: Mapped[int] = mapped_column(ForeignKey("pillars.id"), nullable=False)
    processed_indicator_id: Mapped[int] = mapped_column(ForeignKey("processed_indicators.id"), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        UniqueConstraint("pillar_id", "processed_indicator_id", name="uq_pillar_component"),
    )