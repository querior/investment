from app.services.allocation.engine import compute_allocation_deltas

def test_allocation_deltas_are_neutral():
  pillars = {
    "Growth": 0.0,
    "Inflation": 0.0,
    "Policy": 0.0,
    "Risk": 0.0,
  }
  
  deltas = compute_allocation_deltas(pillars)
  
  for delta in deltas.values():
    assert abs(delta) < 1e-6