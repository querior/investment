from app.db.session import engine, Base

# importa tutti i modelli per registrarli su Base.metadata
from app.db.macro_raw import MacroRaw
from app.db.macro_processed import MacroProcessed
from app.db.macro_pillar import MacroPillar
from app.db.market_price import MarketPrice
from app.db.meta_ingestion import IngestionState
from app.db.user import User

def init_db():
    Base.metadata.create_all(bind=engine)