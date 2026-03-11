from datetime import date
import argparse
from typing import cast

from app.db.session import SessionLocal
from app.backtest.init_db import init_backtest_db
from app.backtest.runs import run_backtest

def parse_args():
    parser = argparse.ArgumentParser("Run macro backtest")
    parser.add_argument("--start", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date YYYY-MM-DD")
    return parser.parse_args()

def main():
    args = parse_args()
    
    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end)
    
    db = SessionLocal()

    try:
        init_backtest_db()


        run_id = run_backtest(
            db=db,
            name="Macro Allocation v1",
            strategy_version="v1.0",
            start=start,
            end=end,
        )

        print("Backtest completed:", run_id)
    finally:
        db.close()
        

if __name__ == "__main__":
    main()