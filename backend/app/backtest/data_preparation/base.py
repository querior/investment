import datetime
import pandas as pd
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.backtest.schemas import BacktestRunParameter
from app.db.market_price import MarketPrice


def prepare_market_df(db: Session, run, warmup_days: int = 260):
    """
    Prepare base market data for backtest execution.

    Extracts parameters, loads market data with warmup period.

    Args:
        db: Database session
        run: BacktestRun object with start_date and end_date
        warmup_days: Number of days to load before start_date for warmup (default: 40)

    Returns:
        pd.DataFrame: Market data for the backtest period
    """
    params = db.query(BacktestRunParameter).filter(BacktestRunParameter.run_id == run.id).all()
    if not params:
        run.error_message = "Undefined params for backtest"
        db.commit()
        raise HTTPException(status_code=404, detail="Undefined params for backtest")
    params_dict = {
        p.key: {
            "value": p.value,
            "unit": p.unit,
        }
        for p in params
    }

    symbol = params_dict.get("symbol")
    symbol_str = symbol.get("value") if isinstance(symbol, dict) else symbol

    if not symbol_str or not params_dict.get("initial_capital"):
        run.error_message = "Undefined params initial_capital for backtest"
        db.commit()
        raise HTTPException(status_code=400, detail="Undefined params initial_capital for backtest")

    load_start = run.start_date - datetime.timedelta(days=warmup_days) # type: ignore
    load_end = run.end_date

    data = db.query(MarketPrice).filter(
               MarketPrice.symbol == symbol_str,
               MarketPrice.date >= load_start,
               MarketPrice.date <= load_end
            ).all()
    rows = [
        {
            "symbol": x.symbol,
            "date": x.date,
            "open": x.open,
            "low": x.low,
            "high": x.high,
            "close": x.close,
            "volume": x.volume,
        }
        for x in data
    ]
    df = pd.DataFrame(rows, columns=["symbol", "date","open", "high", "low", "close", "volume"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.reset_index(drop=True)

    return df
