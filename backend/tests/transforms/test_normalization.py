import pandas as pd
from app.services.transforms.normalization import compute_z_score, clip

# def test_z_score_mean_zero():
#   s = pd.Series(range(1,101))
#   z = compute_z_score(s, window=20).dropna()
#   assert round(z.mean(),6) == 0

# def test_clipping():
#   s = pd.Series([0,0,0,10])
#   clipped = clip(s, limit=3)
#   assert clipped.max() == 3