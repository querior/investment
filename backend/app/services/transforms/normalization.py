import pandas as pd

def compute_z_score(series: pd.Series, window: int) -> pd.Series:
  mean = series.rolling(window).mean()
  std = series.rolling(window).std()

  return (series - mean) / std

def clip(series: pd.Series, limit: float =3.0) -> pd.Series:
  return series.clip(lower=-limit, upper=limit)