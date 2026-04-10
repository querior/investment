import pandas as pd
import numpy as np
from typing import cast

def enrich_with_iv(df: pd.DataFrame, alpha: float = 4.0, iv_min: float = 0.10, iv_max: float = 0.80) -> pd.DataFrame:
    df = df.sort_values("date").copy()
    log_ret = cast(pd.Series, np.log(df["close"] / df["close"].shift(1)))
    rv_20 = log_ret.rolling(20).std()
    iv = 1.15 * np.sqrt(252) * rv_20 + alpha * (-log_ret).clip(lower=0)
    df["iv"] = iv.clip(lower=iv_min, upper=iv_max)
    df = df.dropna(subset=["iv"])
    return df