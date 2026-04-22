import pandas as pd
import numpy as np


def add_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Add Average Directional Index (ADX) to dataframe.

    ADX measures trend strength (0-100), independent of direction.
    ADX > 25 = strong trend (direzionale)
    ADX < 25 = sideways market

    Calculation:
    1. Calculate +DM, -DM (directional movements)
    2. Calculate True Range (TR)
    3. Normalize with TR → +DI, -DI
    4. ADX = EMA(|+DI - -DI| / (+DI + -DI), period)

    Args:
        df: DataFrame with 'high', 'low', 'close' columns
        period: ADX period (default: 14)

    Returns:
        pd.DataFrame: DataFrame with added 'adx', 'plus_di', 'minus_di' columns
    """
    df = df.copy()

    # --- True Range ---
    high_low = df["high"] - df["low"]
    high_close = abs(df["high"] - df["close"].shift())
    low_close = abs(df["low"] - df["close"].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

    # --- Directional Movements ---
    up_move = df["high"].diff()
    down_move = -df["low"].diff()

    plus_dm = np.where(
        (up_move > down_move) & (up_move > 0), up_move, 0.0
    )
    minus_dm = np.where(
        (down_move > up_move) & (down_move > 0), down_move, 0.0
    )

    # --- Smooth TR, +DM, -DM over period ---
    tr_smooth = _smooth_series(tr, period)
    plus_dm_smooth = _smooth_series(pd.Series(plus_dm, index=df.index), period).values
    minus_dm_smooth = _smooth_series(pd.Series(minus_dm, index=df.index), period).values

    # --- Directional Indicators ---
    plus_di = np.where(
        tr_smooth > 0,
        (plus_dm_smooth / tr_smooth) * 100,
        0.0
    )
    minus_di = np.where(
        tr_smooth > 0,
        (minus_dm_smooth / tr_smooth) * 100,
        0.0
    )

    df["plus_di"] = plus_di
    df["minus_di"] = minus_di

    # --- ADX ---
    di_sum = plus_di + minus_di
    di_diff = np.abs(plus_di - minus_di)

    # Evita divide by zero warning usando np.divide con where
    dx = np.divide(
        di_diff,
        di_sum,
        out=np.zeros_like(di_diff),
        where=di_sum != 0
    ) * 100

    # ADX è EMA del DX
    adx = pd.Series(dx, index=df.index).ewm(span=period, adjust=False).mean()
    df["adx"] = adx

    return df


def _smooth_series(series: pd.Series, period: int) -> pd.Series:
    """
    Smooth series using the Wilder's smoothing method (used in RSI/ADX).

    First value: SMA(period)
    Subsequent values: (prev_smooth × (period-1) + current) / period
    """
    smoothed = pd.Series(index=series.index, dtype=float)

    # Primo valore: SMA
    smoothed.iloc[period - 1] = series.iloc[:period].mean()

    # Valori successivi: Wilder's smoothing
    for i in range(period, len(series)):
        smoothed.iloc[i] = (
            (smoothed.iloc[i - 1] * (period - 1) + series.iloc[i]) / period
        )

    return smoothed
