import enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, Float, ForeignKey, Enum as SAEnum
from app.db.session import Base


class TransformType(str, enum.Enum):
    YOY = "YOY"
    LEVEL = "LEVEL"
    DELTA = "DELTA"


class ResampleMethod(str, enum.Enum):
    MONTHLY_MEAN = "MONTHLY_MEAN"


class ProcessedIndicator(Base):
    __tablename__ = "processed_indicators"

    id: Mapped[int] = mapped_column(primary_key=True)
    output_name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    source_indicator_id: Mapped[int] = mapped_column(ForeignKey("macro_indicators.id"), nullable=False)
    transform: Mapped[TransformType] = mapped_column(SAEnum(TransformType, name="transform_type"), nullable=False)
    resample: Mapped[ResampleMethod | None] = mapped_column(SAEnum(ResampleMethod, name="resample_method"), nullable=True)
    z_score_window: Mapped[int] = mapped_column(nullable=False, default=60)
    z_score_clip: Mapped[float] = mapped_column(Float, nullable=False, default=3.0)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    invert: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)