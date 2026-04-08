from __future__ import annotations
from app.backtest.models import OptionLeg, Position
from app.backtest.option.pricing import OptionState

def should_close_position(position: Position) -> bool:
  current_value = position.price
  pnl = current_value - position.initial_value
  
  # profitto > 50% del credito iniziale assoluto
  if position.initial_value < 0 and pnl >= abs(position.initial_value)*0.5:
    return True
  
  # chiusura a 21 DTE
  min_t = min(leg.state.T for leg in position.legs)
  if min_t <= 21 / 365.0:
    return True
  
  return False

def create_bull_put_spread(
    date: str,
    S: float,
    iv: float,
    dte_days: int = 45,
    r: float = 0.03,
    quantity: int = 1,
) -> Position:
  T = dte_days / 365.0

  short_strike = round(S * 0.95, 0)
  long_strike = round(S * 0.92, 0)

  short_put = OptionLeg(
    sign=-1,
    quantity=quantity,
    state=OptionState(
      option_type="put",
      S=S,
      K=short_strike,
      T=T,
      r=r,
      sigma=iv,
    ),
  )

  long_put = OptionLeg(
    sign=+1,
    quantity=quantity,
    state=OptionState(
      option_type="put",
      S=S,
      K=long_strike,
      T=T,
      r=r,
      sigma=iv,
    ),
  )

  return Position(
    name="bull_put_spread",
    legs=[short_put, long_put],
    opened_at=date,
  )