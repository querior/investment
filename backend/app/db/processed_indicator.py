import enum
from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, Enum as SAEnum
from app.db.session import Base


class TransformType(str, enum.Enum):
    YOY = "YOY"
    LEVEL = "LEVEL"
    DELTA = "DELTA"


class ResampleMethod(str, enum.Enum):
    MONTHLY_MEAN = "MONTHLY_MEAN"


class ProcessedIndicator(Base):
    __tablename__ = "processed_indicators"

    id = Column(Integer, primary_key=True)
    output_name = Column(String, unique=True, nullable=False)
    source_indicator_id = Column(Integer, ForeignKey("macro_indicators.id"), nullable=False)
    transform = Column(SAEnum(TransformType, name="transform_type"), nullable=False)
    resample = Column(SAEnum(ResampleMethod, name="resample_method"), nullable=True)
    z_score_window = Column(Integer, nullable=False, default=60)
    z_score_clip = Column(Float, nullable=False, default=3.0)
    is_active = Column(Boolean, nullable=False, default=True)
