import pandas as pd
import numpy as np


def add_ttm_squeeze(
    df: pd.DataFrame,
    bb_percentile: int = 20,
    macd_threshold: float = 0.5,
    lookback_for_percentile: int = 60
) -> pd.DataFrame:
    """
    Add TTM Squeeze indicator.

    TTM Squeeze signals when Bollinger Bands are tight (volatility low)
    and MACD is near zero (momentum flat).

    This indicates potential breakout setup (volatility expansion imminent).

    Args:
        df: DataFrame with 'boll_width' and 'macd' columns (must be pre-calculated)
        bb_percentile: Percentile threshold for BB width (default: 20 = bottom 20%)
        macd_threshold: Threshold for MACD flatness (default: 0.5)
        lookback_for_percentile: Rolling window for BB width percentile (default: 60)

    Returns:
        pd.DataFrame: DataFrame with added 'squeeze_active', 'squeeze_intensity' columns
    """
    df = df.copy()

    if "boll_width" not in df.columns:
        raise ValueError("DataFrame must contain 'boll_width' column (from add_range_features)")
    if "macd" not in df.columns:
        raise ValueError("DataFrame must contain 'macd' column (from add_momentum_features)")

    # --- Bollinger Bands squeeze: BB width in bottom 20% ---
    bb_percentile_value = df["boll_width"].rolling(
        window=lookback_for_percentile, min_periods=1
    ).quantile(bb_percentile / 100.0)

    squeeze_bb = df["boll_width"] < bb_percentile_value

    # --- MACD flatness: MACD vicino a zero ---
    squeeze_macd = np.abs(df["macd"]) < macd_threshold

    # --- TTM Squeeze: both conditions met ---
    df["squeeze_active"] = squeeze_bb & squeeze_macd

    # --- Squeeze intensity: quanto è stretta la BB (0-100 percentile) ---
    # raw=True → pandas passa un array NumPy, non una Series
    # Questo permette di usare x[-1] per accedere all'ultimo elemento per posizione
    df["squeeze_intensity"] = df["boll_width"].rolling(
        window=lookback_for_percentile, min_periods=1
    ).apply(lambda x: (x[-1] < x).sum() / len(x) * 100 if len(x) > 0 else np.nan, raw=True)

    return df


def add_volume_metrics(df: pd.DataFrame, sma_period: int = 20) -> pd.DataFrame:
    """
    Add volume-based metrics.

    Calculates:
    - volume_sma: Simple moving average of volume
    - volume_ratio: Current volume / SMA volume (1.0 = neutral, >1 = expansion, <1 = compression)

    Args:
        df: DataFrame with 'volume' column
        sma_period: Period for volume SMA (default: 20)

    Returns:
        pd.DataFrame: DataFrame with added 'volume_sma', 'volume_ratio' columns
    """
    df = df.copy()

    if "volume" not in df.columns:
        raise ValueError("DataFrame must contain 'volume' column")

    df["volume_sma"] = df["volume"].rolling(window=sma_period, min_periods=1).mean()

    df["volume_ratio"] = np.where(
        df["volume_sma"] > 0,
        df["volume"] / df["volume_sma"],
        1.0
    )

    return df
