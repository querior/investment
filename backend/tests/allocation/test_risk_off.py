from app.services.allocation.engine import compute_allocation_deltas

def test_risk_off_scenario():
  pillars = {
    "Growth": -2.0,
    "Inflation": 0.0,
    "Policy": 0.0,
    "Risk": 2.0,
  }
  
  deltas = compute_allocation_deltas(pillars)
  
  assert deltas["Equity"] <0
  assert deltas["Cash"] > 0