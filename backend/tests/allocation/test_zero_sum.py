from app.services.allocation.engine import compute_allocation_deltas

def test_allocation_deltas_are_zero_sum():
  pillars = {
    "Growth": 1.0,
    "Inflation": -0.5,
    "Policy": 0.0,
    "Risk": 0.5,
  }
  
  deltas = compute_allocation_deltas(pillars)
  
  assert abs(sum(deltas.values())) < 1e-6