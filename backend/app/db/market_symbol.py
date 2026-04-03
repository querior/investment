import enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean, Enum as SAEnum
from app.db.session import Base


class MarketSource(str, enum.Enum):
    YAHOO = "YAHOO"
    IBKR = "IBKR"


class AssetType(str, enum.Enum):
    ETF = "ETF"
    STOCK = "STOCK"
    FUTURE = "FUTURE"
    OPTION = "OPTION"


class MarketSymbol(Base):
    __tablename__ = "market_symbols"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[MarketSource] = mapped_column(SAEnum(MarketSource, name="market_source"), nullable=False)
    asset_type: Mapped[AssetType] = mapped_column(SAEnum(AssetType, name="asset_type"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)