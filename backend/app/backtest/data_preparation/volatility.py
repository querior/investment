import pandas as pd
import numpy as np
from typing import cast


def add_realized_volatility_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add realized volatility features to dataframe.

    Args:
        df: DataFrame with 'close' column

    Returns:
        pd.DataFrame: DataFrame with added 'rv_20' column
    """
    df = df.copy()
    log_ret = cast(pd.Series, np.log(df["close"] / df["close"].shift(1)))
    rv_20 = log_ret.rolling(20).std() * np.sqrt(252)
    df["rv_20"] = rv_20
    return df


def enrich_with_iv(df: pd.DataFrame, alpha: float = 4.0, iv_min: float = 0.10, iv_max: float = 0.80) -> pd.DataFrame:
    df = df.sort_values("date").copy()
    log_ret = cast(pd.Series, np.log(df["close"] / df["close"].shift(1)))
    rv_20 = log_ret.rolling(20).std()
    iv = 1.15 * np.sqrt(252) * rv_20 + alpha * (-log_ret).clip(lower=0)
    df["iv"] = iv.clip(lower=iv_min, upper=iv_max)
    df = df.dropna(subset=["iv"])
    return df


def calculate_iv_rv_ratio(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate implied volatility to realized volatility ratio.

    Formula: iv_rv_ratio = iv / rv if rv > 0 else 1.0

    Args:
        df: DataFrame with 'iv' and 'rv_20' columns

    Returns:
        pd.DataFrame: DataFrame with added 'iv_rv_ratio' column
    """
    df = df.copy()
    df["iv_rv_ratio"] = np.where(
        df["rv_20"] > 0,
        df["iv"] / df["rv_20"],
        1.0
    )
    return df
