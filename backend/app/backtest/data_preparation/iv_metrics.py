import pandas as pd
import numpy as np
from typing import cast


def add_iv_rank_and_percentile(df: pd.DataFrame, lookback_days: int = 252) -> pd.DataFrame:
    """
    Add IV Rank and IV Percentile to dataframe.

    IV Rank = (IV_current - IV_min_lookback) / (IV_max_lookback - IV_min_lookback) × 100
    IV Percentile = percentile rank della IV corrente nei giorni precedenti

    Args:
        df: DataFrame with 'iv' column
        lookback_days: Rolling window for min/max (default: 252 = 52 weeks)

    Returns:
        pd.DataFrame: DataFrame with added 'iv_rank' and 'iv_percentile' columns
    """
    df = df.copy()

    # Rolling min/max per IV Rank
    rolling_min = df["iv"].rolling(window=lookback_days, min_periods=1).min()
    rolling_max = df["iv"].rolling(window=lookback_days, min_periods=1).max()

    # Evita divisione per zero
    iv_range = rolling_max - rolling_min
    iv_rank = np.where(
        iv_range > 0,
        ((df["iv"] - rolling_min) / iv_range) * 100,
        50.0  # Se range è 0 (tutte IV uguali), default a 50
    )
    df["iv_rank"] = iv_rank

    # IV Percentile — percentile della IV nella rolling window
    def calculate_percentile(series: pd.Series) -> float:
        """Calcola il percentile della IV corrente rispetto alla finestra rolling."""
        if len(series) == 0 or pd.isna(series.iloc[-1]):
            return np.nan
        current = series.iloc[-1]
        window = series.dropna()
        if len(window) == 0:
            return np.nan
        return (window < current).sum() / len(window) * 100

    iv_percentile = df["iv"].rolling(window=lookback_days, min_periods=1).apply(
        calculate_percentile, raw=False
    )
    df["iv_percentile"] = iv_percentile

    return df
