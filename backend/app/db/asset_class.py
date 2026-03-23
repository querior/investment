from sqlalchemy import Column, Integer, String, Float, ForeignKey
from app.db.session import Base


class AssetClass(Base):
    __tablename__ = "asset_classes"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    neutral_weight = Column(Float, nullable=False)
    max_weight = Column(Float, nullable=False)
    proxy_id = Column(Integer, ForeignKey("market_symbols.id"), nullable=False)
    display_order = Column(Integer, nullable=False, default=0)
