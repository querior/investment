from sqlalchemy import text
from app.db.session import engine, Base

from app.backtest.schemas.backtest import Backtest
from app.backtest.schemas.backtest_run import BacktestRun
from app.backtest.schemas.backtest_weight import BacktestWeight
from app.backtest.schemas.backtest_performance import BacktestPerformance
from app.backtest.schemas.backtest_run_parameter import BacktestRunParameter
from app.backtest.schemas.option_strategy import OptionStrategy
from app.backtest.schemas.backtest_position import BacktestPosition
from app.backtest.schemas.backtest_position_snapshot import BacktestPositionSnapshot
from app.backtest.schemas.backtest_portfolio_performance import BacktestPortfolioPerformance
from app.backtest.schemas.instrument_config import InstrumentConfig

_TABLES = [
    Backtest.__table__,
    BacktestRun.__table__,
    BacktestWeight.__table__,
    BacktestPerformance.__table__,
    BacktestRunParameter.__table__,
    OptionStrategy.__table__,
    BacktestPosition.__table__,
    BacktestPositionSnapshot.__table__,
    BacktestPortfolioPerformance.__table__,
    InstrumentConfig.__table__,
]

_INSTRUMENT_SEED = [
    {
        "ticker": "IWM",
        "name": "iShares Russell 2000 ETF",
        "dividend_yield": 0.015,
        "iv_proxy": "RVX",
        "iv_alpha": 4.0,
        "contract_multiplier": 100,
        "settlement": "physical",
        "iv_min": 0.10,
        "iv_max": 0.80,
        "commission_per_contract": 0.65,
        "min_commission": 1.00,
        "bid_ask_spread_pct": 0.02,
    },
    {
        "ticker": "SPY",
        "name": "SPDR S&P 500 ETF",
        "dividend_yield": 0.013,
        "iv_proxy": "VIX",
        "iv_alpha": 3.2,
        "contract_multiplier": 100,
        "settlement": "physical",
        "iv_min": 0.10,
        "iv_max": 0.80,
        "commission_per_contract": 0.65,
        "min_commission": 1.00,
        "bid_ask_spread_pct": 0.01,
    },
    {
        "ticker": "QQQ",
        "name": "Invesco QQQ Trust",
        "dividend_yield": 0.006,
        "iv_proxy": "VXN",
        "iv_alpha": 4.5,
        "contract_multiplier": 100,
        "settlement": "physical",
        "iv_min": 0.10,
        "iv_max": 0.80,
        "commission_per_contract": 0.65,
        "min_commission": 1.00,
        "bid_ask_spread_pct": 0.015,
    },
    {
        "ticker": "SPX",
        "name": "S&P 500 Index",
        "dividend_yield": 0.013,
        "iv_proxy": "VIX",
        "iv_alpha": 3.2,
        "contract_multiplier": 100,
        "settlement": "cash",
        "iv_min": 0.10,
        "iv_max": 0.80,
        "commission_per_contract": 1.00,
        "min_commission": 1.00,
        "bid_ask_spread_pct": 0.005,
    },
]


def _seed_instruments(conn) -> None:
    for row in _INSTRUMENT_SEED:
        conn.execute(text("""
            INSERT INTO instrument_configs (
                ticker, name, dividend_yield, iv_proxy, iv_alpha,
                contract_multiplier, settlement, iv_min, iv_max,
                commission_per_contract, min_commission, bid_ask_spread_pct
            ) VALUES (
                :ticker, :name, :dividend_yield, :iv_proxy, :iv_alpha,
                :contract_multiplier, :settlement, :iv_min, :iv_max,
                :commission_per_contract, :min_commission, :bid_ask_spread_pct
            )
            ON CONFLICT (ticker) DO NOTHING
        """), row)


def init_backtest_db(reset: bool = False) -> None:
    if reset:
        with engine.begin() as conn:
            conn.execute(text("""
                DROP TABLE IF EXISTS backtest_performance CASCADE;
                DROP TABLE IF EXISTS backtest_weights CASCADE;
                DROP TABLE IF EXISTS backtest_runs CASCADE;
                DROP TABLE IF EXISTS backtests CASCADE;
                DROP TYPE IF EXISTS backteststatus CASCADE;
            """))
    Base.metadata.create_all(bind=engine, tables=_TABLES)
    # Migrazione incrementale: aggiunge colonne introdotte dopo la creazione iniziale
    with engine.begin() as conn:
        conn.execute(text("""
            ALTER TABLE backtests
                ADD COLUMN IF NOT EXISTS frequency     VARCHAR DEFAULT 'EOM',
                ADD COLUMN IF NOT EXISTS instrument    VARCHAR;
            ALTER TABLE backtest_runs
                ADD COLUMN IF NOT EXISTS frequency        VARCHAR DEFAULT 'EOM',
                ADD COLUMN IF NOT EXISTS config_snapshot  VARCHAR,
                ADD COLUMN IF NOT EXISTS win_rate         FLOAT,
                ADD COLUMN IF NOT EXISTS profit_factor    FLOAT,
                ADD COLUMN IF NOT EXISTS n_trades         INTEGER;
            ALTER TABLE backtest_weights
                ADD COLUMN IF NOT EXISTS pillar_scores VARCHAR;
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'backtest_performance'
                      AND column_name = 'monthly_return'
                ) THEN
                    ALTER TABLE backtest_performance
                        RENAME COLUMN monthly_return TO period_return;
                END IF;
            END $$;
            CREATE TABLE IF NOT EXISTS backtest_run_parameters (
                id     SERIAL PRIMARY KEY,
                run_id INTEGER NOT NULL REFERENCES backtest_runs(id) ON DELETE CASCADE,
                key    VARCHAR NOT NULL,
                value  VARCHAR NOT NULL,
                unit   VARCHAR DEFAULT 'value',
                UNIQUE (run_id, key)
            );
            ALTER TABLE backtest_run_parameters
                ADD COLUMN IF NOT EXISTS unit VARCHAR DEFAULT 'value';
            -- Ricrea FK con ON DELETE CASCADE se non già presente
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.referential_constraints rc
                    JOIN information_schema.table_constraints tc
                      ON rc.constraint_name = tc.constraint_name
                    WHERE tc.table_name = 'backtest_weights'
                      AND rc.delete_rule = 'CASCADE'
                ) THEN
                    ALTER TABLE backtest_weights
                        DROP CONSTRAINT IF EXISTS backtest_weights_run_id_fkey;
                    ALTER TABLE backtest_weights
                        ADD CONSTRAINT backtest_weights_run_id_fkey
                        FOREIGN KEY (run_id) REFERENCES backtest_runs(id) ON DELETE CASCADE;
                END IF;
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.referential_constraints rc
                    JOIN information_schema.table_constraints tc
                      ON rc.constraint_name = tc.constraint_name
                    WHERE tc.table_name = 'backtest_performance'
                      AND rc.delete_rule = 'CASCADE'
                ) THEN
                    ALTER TABLE backtest_performance
                        DROP CONSTRAINT IF EXISTS backtest_performance_run_id_fkey;
                    ALTER TABLE backtest_performance
                        ADD CONSTRAINT backtest_performance_run_id_fkey
                        FOREIGN KEY (run_id) REFERENCES backtest_runs(id) ON DELETE CASCADE;
                END IF;
            END $$;
            -- Colonne EV su backtest_positions
            ALTER TABLE backtest_positions
                ADD COLUMN IF NOT EXISTS entry_ev_gross          FLOAT,
                ADD COLUMN IF NOT EXISTS entry_ev_net            FLOAT,
                ADD COLUMN IF NOT EXISTS entry_prob_profit       FLOAT,
                ADD COLUMN IF NOT EXISTS entry_transaction_costs FLOAT,
                ADD COLUMN IF NOT EXISTS entry_fair_value        FLOAT;
        """))
    with engine.begin() as conn:
        _seed_instruments(conn)
