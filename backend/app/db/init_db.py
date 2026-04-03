from sqlalchemy import text
from app.db.session import engine, Base

# config entities (parent — referenziate da FK)
from app.db.macro_indicator import MacroIndicator
from app.db.market_symbol import MarketSymbol
from app.db.processed_indicator import ProcessedIndicator
from app.db.pillar import Pillar
from app.db.pillar_component import PillarComponent
from app.db.asset_class import AssetClass
from app.db.allocation_parameter import AllocationParameter

# tabelle dati (child — hanno FK verso le config entities)
from app.db.macro_raw import MacroRaw
from app.db.macro_processed import MacroProcessed
from app.db.macro_regimes import MacroRegime
from app.db.market_price import MarketPrice
from app.db.meta_ingestion import IngestionState
from app.db.user import User
from app.db.allocation_history import AllocationHistory


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate()


def _migrate() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            -- Migrazione allocation_history: aggiunge id SERIAL come PK e run_id per isolamento backtest
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'allocation_history' AND column_name = 'id'
                ) THEN
                    -- Aggiunge colonna run_id (backtest isolation)
                    ALTER TABLE allocation_history
                        ADD COLUMN run_id INTEGER REFERENCES backtest_runs(id) ON DELETE CASCADE;

                    -- Aggiunge id come nuova PK seriale
                    ALTER TABLE allocation_history ADD COLUMN id SERIAL;
                    ALTER TABLE allocation_history DROP CONSTRAINT IF EXISTS allocation_history_pkey;
                    ALTER TABLE allocation_history ADD PRIMARY KEY (id);

                    -- Unique index parziale: live (run_id IS NULL) e per-run
                    CREATE UNIQUE INDEX allocation_history_live_uq
                        ON allocation_history (date, asset) WHERE run_id IS NULL;
                    CREATE UNIQUE INDEX allocation_history_run_uq
                        ON allocation_history (date, asset, run_id) WHERE run_id IS NOT NULL;
                END IF;
            END $$;
        """))