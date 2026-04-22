import pandas as pd
from app.backtest.data_preparation.base import prepare_market_df
from app.backtest.data_preparation.volatility import enrich_with_iv, add_realized_volatility_features, calculate_iv_rv_ratio
from app.backtest.data_preparation.iv_metrics import add_iv_rank_and_percentile
from app.backtest.data_preparation.trend import add_trend_features
from app.backtest.data_preparation.trend_strength import add_adx
from app.backtest.data_preparation.momentum import add_momentum_features
from app.backtest.data_preparation.range import add_range_features
from app.backtest.data_preparation.squeeze import add_ttm_squeeze, add_volume_metrics
from app.backtest.data_preparation.macro import add_macro_features


def build_backtest_dataset(df: pd.DataFrame, db, params_dict: dict, run) -> pd.DataFrame:
    """
    Build complete backtest dataset with all features and enrichment.

    Executes the full pipeline:
    1. Prepare base market data
    2. Enrich with IV
    3. Add realized volatility features + IV Rank + IV Percentile (TIER 1 CRITICAL)
    4. Add trend features + ADX (TIER 1 CRITICAL)
    5. Add momentum features
    6. Add range features
    7. Add TTM Squeeze + Volume Metrics (TIER 2 MEDIA)
    8. Add macro features
    9. Filter for backtest period (start_date to end_date)

    Args:
        df: Initial market dataframe (usually from prepare_market_df)
        db: Database session
        params_dict: Dictionary containing parameters including IV parameters
        run: BacktestRun object with start_date and end_date

    Returns:
        pd.DataFrame: Complete backtest dataset with all features
    """

    # --- 1. Enrich with IV ---
    alpha_volatility = params_dict.get("alpha_volatility")
    iv_min = params_dict.get("iv_min")
    iv_max = params_dict.get("iv_max")

    df = enrich_with_iv(
        df,
        alpha=float(alpha_volatility["value"]) if alpha_volatility else 4.0,
        iv_min=float(iv_min["value"]) if iv_min else 0.10,
        iv_max=float(iv_max["value"]) if iv_max else 0.80,
    )

    # --- 2. Volatility features (TIER 1 CRITICAL) ---
    df = add_realized_volatility_features(df)
    df = calculate_iv_rv_ratio(df)

    # IV Rank and Percentile (TIER 1 CRITICAL)
    iv_rank_lookback = params_dict.get("iv_rank.lookback_days")
    iv_rank_lookback_days = int(iv_rank_lookback["value"]) if iv_rank_lookback else 252
    df = add_iv_rank_and_percentile(df, lookback_days=iv_rank_lookback_days)

    # --- 3. Trend features (TIER 1 CRITICAL) ---
    df = add_trend_features(df)

    # ADX (TIER 1 CRITICAL)
    adx_period = params_dict.get("adx.period")
    adx_period_val = int(adx_period["value"]) if adx_period else 14
    df = add_adx(df, period=adx_period_val)

    # --- 4. Momentum features ---
    df = add_momentum_features(df)

    # --- 5. Range features ---
    df = add_range_features(df)

    # --- 6. Squeeze and Volume (TIER 2 MEDIA) ---
    squeeze_bb_percentile = params_dict.get("squeeze.bb_percentile")
    squeeze_bb_percentile_val = int(squeeze_bb_percentile["value"]) if squeeze_bb_percentile else 20

    squeeze_macd_threshold = params_dict.get("squeeze.macd_threshold")
    squeeze_macd_threshold_val = float(squeeze_macd_threshold["value"]) if squeeze_macd_threshold else 0.5

    df = add_ttm_squeeze(
        df,
        bb_percentile=squeeze_bb_percentile_val,
        macd_threshold=squeeze_macd_threshold_val
    )

    volume_sma_period = params_dict.get("volume.sma_period")
    volume_sma_period_val = int(volume_sma_period["value"]) if volume_sma_period else 20
    df = add_volume_metrics(df, sma_period=volume_sma_period_val)

    # --- 7. Macro features ---
    df = add_macro_features(df, db)

    # --- 8. Filter for backtest period (remove warmup period) ---
    df = df[(df["date"] >= pd.Timestamp(run.start_date)) & (df["date"] <= pd.Timestamp(run.end_date))] # type: ignore

    return df
