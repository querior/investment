import pandas as pd
from app.services.transforms.normalization import compute_z_score, clip

def test_z_score_zero_when_constant():
  s = pd.Series([10] * 100)
  z = compute_z_score(s, window=20)
  z = z.dropna()

  assert (z.abs() < 1e-6).all()

def test_z_score_increases_with_trend():
  s = pd.Series(range(100))
  z = compute_z_score(s, window=20)

  # ultimi valori devono essere positivi
  assert z.dropna().iloc[-1] > 0

def test_clipping():
  s = pd.Series([-10, 0, 10])
  clipped = clip(s, limit=3)

  assert clipped.min() == -3
  assert clipped.max() == 3

def test_clipping():
  s = pd.Series([0,0,0,10])
  clipped = clip(s, limit=3)
  assert clipped.max() ==3