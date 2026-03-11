from app.services.allocation.engine import compute_allocation_deltas

def test_allocation_deltas_are_capped():
  pillars = {
    "Growth": 3.0,
    "Inflation": 3.0,
    "Policy": 3.0,
    "Risk": 3.0,
  }
  
  deltas = compute_allocation_deltas(pillars)
  
  for delta in deltas.values():
    assert abs(delta) <= 0.10 # 10%