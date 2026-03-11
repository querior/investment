from app.services.allocation.engine import compute_allocation_deltas
import math

def test_allocation_no_nan():
  pillars = {
    "Growth": 1.2,
    "Inflation": -0.7,
    "Policy": 0.3,
    "Risk": -1.1,
  }
  
  deltas = compute_allocation_deltas(pillars)
  
  allowed = {"Equity", "Bond", "Commodities", "Cash"}
  
  for k in allowed:
    assert k in deltas, f"{k} mancante in deltas"
    delta = deltas[k]
    assert delta is not None
    assert not math.isnan(delta)