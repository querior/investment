import pandas as pd
import numpy as np


def add_rsi_14(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add 14-period Relative Strength Index to dataframe.

    Args:
        df: DataFrame with 'close' column

    Returns:
        pd.DataFrame: DataFrame with added 'rsi_14' column
    """
    df = df.copy()
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df["rsi_14"] = 100 - (100 / (1 + rs))
    return df


def add_macd(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add MACD (Moving Average Convergence Divergence) to dataframe.

    MACD = EMA(12) - EMA(26)
    Signal = EMA(9) of MACD
    Histogram = MACD - Signal

    Args:
        df: DataFrame with 'close' column

    Returns:
        pd.DataFrame: DataFrame with added 'macd', 'macd_signal', 'macd_hist' columns
    """
    df = df.copy()
    ema_12 = df["close"].ewm(span=12, adjust=False).mean()
    ema_26 = df["close"].ewm(span=26, adjust=False).mean()

    df["macd"] = ema_12 - ema_26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    return df


def add_momentum_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all momentum features to dataframe.

    Calculates: rsi_14, macd, macd_signal, macd_hist

    Args:
        df: DataFrame with 'close' column

    Returns:
        pd.DataFrame: DataFrame with all momentum features added
    """
    df = add_rsi_14(df)
    df = add_macd(df)
    return df
