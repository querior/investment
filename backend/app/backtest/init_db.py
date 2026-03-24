from sqlalchemy import text
from app.db.session import engine, Base

from app.backtest.schemas.backtest import Backtest
from app.backtest.schemas.backtest_run import BacktestRun
from app.backtest.schemas.backtest_weight import BacktestWeight
from app.backtest.schemas.backtest_performance import BacktestPerformance

_TABLES = [
    Backtest.__table__,
    BacktestRun.__table__,
    BacktestWeight.__table__,
    BacktestPerformance.__table__,
]


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
                ADD COLUMN IF NOT EXISTS primary_index VARCHAR DEFAULT 'MacroScore';
            ALTER TABLE backtest_runs
                ADD COLUMN IF NOT EXISTS frequency        VARCHAR DEFAULT 'EOM',
                ADD COLUMN IF NOT EXISTS primary_index    VARCHAR DEFAULT 'MacroScore',
                ADD COLUMN IF NOT EXISTS config_snapshot  VARCHAR,
                ADD COLUMN IF NOT EXISTS win_rate         FLOAT,
                ADD COLUMN IF NOT EXISTS profit_factor    FLOAT,
                ADD COLUMN IF NOT EXISTS n_trades         INTEGER;
            ALTER TABLE backtest_weights
                ADD COLUMN IF NOT EXISTS macro_score   FLOAT,
                ADD COLUMN IF NOT EXISTS pillar_scores VARCHAR;
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
        """))
