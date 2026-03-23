from sqlalchemy import Column, Integer, Float, ForeignKey, UniqueConstraint
from app.db.session import Base


class SensitivityCoefficient(Base):
    __tablename__ = "sensitivity_coefficients"

    id = Column(Integer, primary_key=True)
    pillar_id = Column(Integer, ForeignKey("pillars.id"), nullable=False)
    asset_class_id = Column(Integer, ForeignKey("asset_classes.id"), nullable=False)
    coefficient = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint("pillar_id", "asset_class_id", name="uq_sensitivity"),
    )
