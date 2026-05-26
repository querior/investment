from sqlalchemy import text
from app.db.session import engine, Base

# config entities (parent — referenziate da FK)
from app.db.macro_indicator import MacroIndicator
from app.db.market_symbol import MarketSymbol
from app.db.processed_indicator import ProcessedIndicator
from app.db.pillar import Pillar
from app.db.pillar_component import PillarComponent
from app.db.asset_class import AssetClass

# tabelle dati (child — hanno FK verso le config entities)
from app.db.macro_raw import MacroRaw
from app.db.macro_processed import MacroProcessed
from app.db.macro_regimes import MacroRegime
from app.db.market_price import MarketPrice
from app.db.meta_ingestion import IngestionState
from app.db.user import User
from app.db.allocation_history import AllocationHistory
from app.db.decision_log import DecisionLog


def init_db():
    _migrate()
    Base.metadata.create_all(bind=engine)


def _migrate() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            -- Aggiunge entry_conditions e exit_conditions a backtest_positions
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'backtest_positions' AND column_name = 'entry_conditions'
                ) THEN
                    ALTER TABLE backtest_positions
                        ADD COLUMN entry_conditions JSONB;
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'backtest_positions' AND column_name = 'exit_conditions'
                ) THEN
                    ALTER TABLE backtest_positions
                        ADD COLUMN exit_conditions JSONB;
                END IF;
            END $$;
            -- Rinomina allocation_parameters → backtest_parameters
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'allocation_parameters'
                ) THEN
                    ALTER TABLE allocation_parameters RENAME TO backtest_parameters;
                END IF;
            END $$;
            -- Aggiunge backtest_id a backtest_parameters
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'backtest_parameters' AND column_name = 'backtest_id'
                ) THEN
                    ALTER TABLE backtest_parameters
                        ADD COLUMN backtest_id INTEGER REFERENCES backtests(id) ON DELETE CASCADE;
                END IF;
            END $$;
            ALTER TABLE backtest_runs ADD COLUMN IF NOT EXISTS max_consecutive_losses INTEGER;
            -- entry_max_loss e entry_max_profit su backtest_positions
            ALTER TABLE backtest_positions ADD COLUMN IF NOT EXISTS entry_max_loss FLOAT;
            ALTER TABLE backtest_positions ADD COLUMN IF NOT EXISTS entry_max_profit FLOAT;
            -- ADR 004: edge_source su decision_logs
            ALTER TABLE decision_logs
                ADD COLUMN IF NOT EXISTS edge_source VARCHAR;
            -- Sub-scores L4 opportunity evaluation
            ALTER TABLE decision_logs ADD COLUMN IF NOT EXISTS pricing_edge_score FLOAT;
            ALTER TABLE decision_logs ADD COLUMN IF NOT EXISTS risk_reward_score FLOAT;
            ALTER TABLE decision_logs ADD COLUMN IF NOT EXISTS breakeven_score FLOAT;
            ALTER TABLE decision_logs ADD COLUMN IF NOT EXISTS execution_cost_score FLOAT;
            ALTER TABLE decision_logs ADD COLUMN IF NOT EXISTS capital_efficiency_score FLOAT;
            -- Leading indicator columns on decision_logs
            ALTER TABLE decision_logs ADD COLUMN IF NOT EXISTS iv_term_slope_delta5 FLOAT;
            ALTER TABLE decision_logs ADD COLUMN IF NOT EXISTS credit_spread_delta5 FLOAT;
            ALTER TABLE decision_logs ADD COLUMN IF NOT EXISTS vvix_rank FLOAT;
            -- Leading indicators: VXVCLS (VIX3M) via FRED → macro_raw
            INSERT INTO macro_indicators (ticker, source, description, frequency, is_active)
            VALUES ('VXVCLS', 'FRED', 'CBOE S&P 500 3-Month Volatility Index (VIX3M)', 'DAILY', true)
            ON CONFLICT (ticker) DO NOTHING;
            -- Leading indicators: ^VVIX via yfinance → market_price
            INSERT INTO market_symbols (symbol, description, source, asset_type, is_active)
            VALUES ('^VVIX', 'CBOE Volatility of Volatility Index', 'YAHOO', 'ETF', true)
            ON CONFLICT (symbol) DO NOTHING;
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