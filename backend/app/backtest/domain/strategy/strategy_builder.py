from __future__ import annotations
from app.backtest.domain.models import OptionLeg, Position
from ..option.pricing import OptionState

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
  
  
def create_bear_call_spread(
    date: str,
    S: float,
    iv: float,
    dte_days: int = 45,
    r: float = 0.03,
    quantity: int = 1,
) -> Position:
    T = dte_days / 365.0

    short_strike = round(S * 1.05, 0)
    long_strike = round(S * 1.08, 0)

    short_call = OptionLeg(
        sign=-1,
        quantity=quantity,
        state=OptionState(
            option_type="call",
            S=S,
            K=short_strike,
            T=T,
            r=r,
            sigma=iv,
        ),
    )

    long_call = OptionLeg(
        sign=+1,
        quantity=quantity,
        state=OptionState(
            option_type="call",
            S=S,
            K=long_strike,
            T=T,
            r=r,
            sigma=iv,
        ),
    )

    return Position(
        name="bear_call_spread",
        legs=[short_call, long_call],
        opened_at=date,
    )


def create_put_broken_wing_butterfly(
  date: str,
  S: float,
  iv: float,
  dte_days: int = 45,
  r: float = 0.03,
  quantity: int = 1,
) -> Position:
  T = dte_days / 365.0

  low_strike = round(S * 0.90, 0)
  mid_strike = round(S * 0.95, 0)
  high_strike = round(S * 0.97, 0)

  long_put_low = OptionLeg(
    sign=+1,
    quantity=quantity,
    state=OptionState(
      option_type="put",
      S=S,
      K=low_strike,
      T=T,
      r=r,
      sigma=iv,
    ),
  )

  short_put_1 = OptionLeg(
    sign=-1,
    quantity=quantity,
    state=OptionState(
      option_type="put",
      S=S,
      K=mid_strike,
      T=T,
      r=r,
      sigma=iv,
    ),
  )

  short_put_2 = OptionLeg(
    sign=-1,
    quantity=quantity,
    state=OptionState(
      option_type="put",
      S=S,
      K=mid_strike,
      T=T,
      r=r,
      sigma=iv,
    ),
  )

  long_put_high = OptionLeg(
    sign=+1,
    quantity=quantity,
    state=OptionState(
      option_type="put",
      S=S,
      K=high_strike,
      T=T,
      r=r,
      sigma=iv,
    ),
  )

  return Position(
    name="put_broken_wing_butterfly",
    legs=[long_put_low, short_put_1, short_put_2, long_put_high],
    opened_at=date,
  )