import pandas as pd
import numpy as np
from sqlalchemy.orm import Session

from app.db.macro_raw import MacroRaw
from app.db.market_price import MarketPrice


_FRED_TICKERS = ["VIXCLS", "VXVCLS", "BAA10Y"]
_MARKET_LEAD_SYMBOLS = ["^VVIX"]
_DELTA_WINDOW = 5      # days for rate-of-change
_RANK_WINDOW = 252     # days for rolling percentile


def add_leading_indicators(df: pd.DataFrame, db: Session) -> pd.DataFrame:
    """
    Add leading indicator columns to the backtest DataFrame.

    Sources:
      - macro_raw   : VIXCLS (VIX 30d), BAA10Y (credit spread) — already ingested via FRED
      - market_price: ^VVIX (VIX of VIX) — ingested via yfinance

    New columns (neutral fallback if data missing):
      - iv_term_slope       : VIXCLS / VXVCLS  (>1 = backwardation = short-term stress)
      - iv_term_slope_delta5: 5-day change of iv_term_slope (negative = stress resolving → good entry)
      - credit_spread_delta5: 5-day change of BAA10Y        (negative = tightening → good entry)
      - vvix_rank           : 252-day rolling percentile of VVIX (0-100, lower = calmer)
    """
    if df.empty:
        return df

    start_date = (df["date"].min() - pd.Timedelta(days=_RANK_WINDOW + _DELTA_WINDOW + 10)).date()
    end_date = df["date"].max().date()

    fred_df   = _load_fred(db, start_date, end_date)
    market_df = _load_market(db, start_date, end_date)
    leads_df  = _compute_signals(fred_df, market_df)

    df = df.merge(leads_df, on="date", how="left")
    df["iv_term_slope"]        = df["iv_term_slope"].fillna(1.0)
    df["iv_term_slope_delta5"] = df["iv_term_slope_delta5"].fillna(0.0)
    df["credit_spread_delta5"] = df["credit_spread_delta5"].fillna(0.0)
    df["vvix_rank"]            = df["vvix_rank"].fillna(50.0)

    return df


def _load_fred(db: Session, start_date, end_date) -> pd.DataFrame:
    rows = (
        db.query(MacroRaw.date, MacroRaw.indicator, MacroRaw.value)
        .filter(
            MacroRaw.indicator.in_(_FRED_TICKERS),
            MacroRaw.date >= start_date,
            MacroRaw.date <= end_date,
        )
        .all()
    )
    if not rows:
        return pd.DataFrame(columns=["date"] + _FRED_TICKERS)

    raw = pd.DataFrame(rows, columns=["date", "indicator", "value"])
    raw["date"] = pd.to_datetime(raw["date"])
    pivoted = raw.pivot(index="date", columns="indicator", values="value").reset_index()
    for col in _FRED_TICKERS:
        if col not in pivoted.columns:
            pivoted[col] = np.nan
    return pivoted


def _load_market(db: Session, start_date, end_date) -> pd.DataFrame:
    rows = (
        db.query(MarketPrice.date, MarketPrice.symbol, MarketPrice.close)
        .filter(
            MarketPrice.symbol.in_(_MARKET_LEAD_SYMBOLS),
            MarketPrice.date >= start_date,
            MarketPrice.date <= end_date,
        )
        .all()
    )
    if not rows:
        return pd.DataFrame(columns=["date", "^VVIX"])

    raw = pd.DataFrame(rows, columns=["date", "symbol", "close"])
    raw["date"] = pd.to_datetime(raw["date"])
    pivoted = raw.pivot(index="date", columns="symbol", values="close").reset_index()
    for col in _MARKET_LEAD_SYMBOLS:
        if col not in pivoted.columns:
            pivoted[col] = np.nan
    return pivoted


def _compute_signals(fred_df: pd.DataFrame, market_df: pd.DataFrame) -> pd.DataFrame:
    # --- Merge all sources on date ---
    if fred_df.empty and market_df.empty:
        return pd.DataFrame(columns=["date", "iv_term_slope", "iv_term_slope_delta5", "credit_spread_delta5", "vvix_rank"])

    if fred_df.empty:
        combined = market_df.copy()
        for col in _FRED_TICKERS:
            combined[col] = np.nan
    elif market_df.empty:
        combined = fred_df.copy()
        for col in _MARKET_LEAD_SYMBOLS:
            combined[col] = np.nan
    else:
        combined = fred_df.merge(market_df, on="date", how="outer")

    combined = combined.sort_values("date").set_index("date")

    # --- IV term structure: VIXCLS / VXVCLS ---
    combined["iv_term_slope"] = combined["VIXCLS"] / combined["VXVCLS"].replace(0, np.nan)
    combined["iv_term_slope_delta5"] = combined["iv_term_slope"].diff(_DELTA_WINDOW)

    # --- Credit spread direction: 5-day delta of BAA10Y ---
    combined["credit_spread_delta5"] = combined["BAA10Y"].diff(_DELTA_WINDOW)

    # --- VVIX rank: 252-day rolling percentile ---
    def _pct_rank(series: pd.Series) -> float:
        if len(series) == 0 or pd.isna(series.iloc[-1]):
            return np.nan
        current = series.iloc[-1]
        window = series.dropna()
        return float((window < current).sum() / len(window) * 100)

    combined["vvix_rank"] = combined["^VVIX"].rolling(_RANK_WINDOW, min_periods=20).apply(_pct_rank, raw=False)

    result = combined[["iv_term_slope", "iv_term_slope_delta5", "credit_spread_delta5", "vvix_rank"]].reset_index()
    return result.sort_values("date").reset_index(drop=True)
