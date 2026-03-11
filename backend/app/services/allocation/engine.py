from .sensitivity import SENSITIVITY
from typing import Dict
from app.services.allocation.config import NEUTRAL_ALLOCATION

ASSETS = ["Equity", "Bond", "Commodities", "Cash"]

K = 0.05          # fattore di scala (5%)
MAX_ABS = 0.10    # cap assoluto ±10%

def f(x: float) -> float:
  """
  Funzione di risposta del pillar.
  Saturazione lineare
  """
  if x > 2.0:
    return 1.0
  if x < -2.0:
    return -1.0
  
  return x/2.0

def compute_allocation_deltas(pillars: Dict[str, float]) -> Dict[str,float]:
  # inizializza tilt grezzi
  raw_tilt = {asset: 0.0 for asset in ASSETS}
  
  # 1) combina pillar x sensitivity
  for pillar, score in pillars.items():
    if pillar not in SENSITIVITY:
      continue
    signal = f(score)
    
    for asset in ASSETS:
      coeff = SENSITIVITY[pillar].get(asset, 0.0)
      raw_tilt[asset] += signal * coeff
  
  # 2) scala
  for asset in ASSETS:
    raw_tilt[asset] *= K
    
  # 3) impone somma zero
  mean_tilt = sum(raw_tilt.values()) / len(raw_tilt)
  deltas = {
    asset: raw_tilt[asset] - mean_tilt
    for asset in ASSETS
  }
  
  # 4) Cap / floor
  for asset in ASSETS:
    if deltas[asset] > MAX_ABS:
      deltas[asset] = MAX_ABS
      
    if deltas[asset] < -MAX_ABS:
      deltas[asset] = -MAX_ABS
      
  # 5) stabilità numerica ( -0.0 -> 0.0)
  deltas = {
    asset: 0.0 if abs(val) < 1e-12 else float(val)
    for asset, val in deltas.items()
  }    
    
  return deltas


def compute_allocation(pillars: dict) -> dict:
    deltas = compute_allocation_deltas(pillars)

    allocation = {
        asset: NEUTRAL_ALLOCATION[asset] + deltas.get(asset, 0.0)
        for asset in NEUTRAL_ALLOCATION
    }

    # rinormalizzazione a 100%
    total = sum(allocation.values())
    allocation = {
        asset: weight / total
        for asset, weight in allocation.items()
    }

    return allocation