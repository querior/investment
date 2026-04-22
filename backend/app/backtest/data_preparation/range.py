import pandas as pd
import numpy as np


def add_atr_14(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add 14-period Average True Range to dataframe.

    ATR measures volatility using high-low-close prices.

    Args:
        df: DataFrame with 'high', 'low', 'close' columns

    Returns:
        pd.DataFrame: DataFrame with added 'atr_14' column
    """
    df = df.copy()

    high_low = df["high"] - df["low"]
    high_close = abs(df["high"] - df["close"].shift())
    low_close = abs(df["low"] - df["close"].shift())

    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df["atr_14"] = true_range.rolling(window=14).mean()

    return df


def add_bollinger_bands(df: pd.DataFrame, period: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """
    Add Bollinger Bands to dataframe.

    Args:
        df: DataFrame with 'close' column
        period: Moving average period (default: 20)
        num_std: Number of standard deviations (default: 2.0)

    Returns:
        pd.DataFrame: DataFrame with added 'boll_mid', 'boll_up', 'boll_down', 'boll_width' columns
    """
    df = df.copy()

    df["boll_mid"] = df["close"].rolling(window=period).mean()
    rolling_std = df["close"].rolling(window=period).std()

    df["boll_up"] = df["boll_mid"] + (rolling_std * num_std)
    df["boll_down"] = df["boll_mid"] - (rolling_std * num_std)
    df["boll_width"] = df["boll_up"] - df["boll_down"]

    return df


def add_range_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add all range/volatility features to dataframe.

    Calculates: atr_14, boll_mid, boll_up, boll_down, boll_width

    Args:
        df: DataFrame with 'high', 'low', 'close' columns

    Returns:
        pd.DataFrame: DataFrame with all range features added
    """
    df = add_atr_14(df)
    df = add_bollinger_bands(df)
    return df
