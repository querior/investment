from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Float, ForeignKey
from app.db.session import Base


class AssetClass(Base):
    __tablename__ = "asset_classes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    neutral_weight: Mapped[float] = mapped_column(Float, nullable=False)
    min_weight: Mapped[float] = mapped_column(Float, default=0.0)
    max_weight: Mapped[float] = mapped_column(Float)
    proxy_id: Mapped[int] = mapped_column(ForeignKey("market_symbols.id"), nullable=False)
    display_order: Mapped[int] = mapped_column(nullable=False, default=0)