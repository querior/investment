import enum
from sqlalchemy import Column, Integer, String, Boolean, Enum as SAEnum
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

    id = Column(Integer, primary_key=True)
    symbol = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=False)
    source = Column(SAEnum(MarketSource, name="market_source"), nullable=False)
    asset_type = Column(SAEnum(AssetType, name="asset_type"), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
