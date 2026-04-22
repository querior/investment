import pandas as pd
import numpy as np


def add_sma_20(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add 20-day simple moving average to dataframe.

    Args:
        df: DataFrame with 'close' column

    Returns:
        pd.DataFrame: DataFrame with added 'sma_20' column
    """
    df = df.copy()
    df["sma_20"] = df["close"].rolling(window=20).mean()
    return df


def add_sma_50(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add 50-day simple moving average to dataframe.

    Args:
        df: DataFrame with 'close' column

    Returns:
        pd.DataFrame: DataFrame with added 'sma_50' column
    """
    df = df.copy()
    df["sma_50"] = df["close"].rolling(window=50).mean()
    return df


def add_ema_20(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add 20-day exponential moving average to dataframe.

    Args:
        df: DataFrame with 'close' column

    Returns:
        pd.DataFrame: DataFrame with added 'ema_20' column
    """
    df = df.copy()
    df["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()
    return df


def add_trend_signal(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add trend signal based on SMA 20/50 spread.

    Signal logic:
    - 1: spread > 1% (bullish trend)
    - -1: spread < -1% (bearish trend)
    - 0: no clear trend

    Args:
        df: DataFrame with 'sma_20' and 'sma_50' columns

    Returns:
        pd.DataFrame: DataFrame with added 'trend_signal' column
    """
    df = df.copy()
    spread = (df["sma_20"] - df["sma_50"]) / df["sma_50"]
    df["trend_signal"] = np.where(
        spread > 0.01, 1,
        np.where(spread < -0.01, -1, 0)
    )
    return df


def add_trend_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all trend features to dataframe.

    Calculates: sma_20, sma_50, ema_20, trend_signal

    Args:
        df: DataFrame with 'close' column

    Returns:
        pd.DataFrame: DataFrame with all trend features added
    """
    df = add_sma_20(df)
    df = add_sma_50(df)
    df = add_ema_20(df)
    df = add_trend_signal(df)
    return df
