from app.db.session import engine, Base

# config entities (parent — referenziate da FK)
from app.db.macro_indicator import MacroIndicator
from app.db.market_symbol import MarketSymbol
from app.db.processed_indicator import ProcessedIndicator
from app.db.pillar import Pillar
from app.db.pillar_component import PillarComponent
from app.db.composite_score import CompositeScore
from app.db.composite_score_weight import CompositeScoreWeight
from app.db.regime_threshold import RegimeThreshold
from app.db.asset_class import AssetClass
from app.db.sensitivity_coefficient import SensitivityCoefficient
from app.db.allocation_parameter import AllocationParameter

# tabelle dati (child — hanno FK verso le config entities)
from app.db.macro_raw import MacroRaw
from app.db.macro_processed import MacroProcessed
from app.db.macro_pillar import MacroPillar
from app.db.market_price import MarketPrice
from app.db.meta_ingestion import IngestionState
from app.db.user import User


def init_db():
    Base.metadata.create_all(bind=engine)