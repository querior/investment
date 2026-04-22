from __future__ import annotations

from app.backtest.domain.models import OptionLeg, Position
from app.backtest.domain.option.pricing import OptionState
from app.backtest.domain.option.strike_selector import find_strike_by_delta


def create_bull_put_spread(
    date: str,
    S: float,
    iv: float,
    dte_days: int = 45,
    r: float = 0.03,
    quantity: int = 1,
    q: float = 0.0,
    target_delta_short: float = 0.16,
    target_delta_long: float = 0.05,
) -> Position:
    T = dte_days / 365.0

    short_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_short, "put")
    long_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_long, "put")

    short_put = OptionLeg(
        sign=-1,
        quantity=quantity,
        state=OptionState(option_type="put", S=S, K=short_strike, T=T, r=r, sigma=iv, q=q),
    )
    long_put = OptionLeg(
        sign=+1,
        quantity=quantity,
        state=OptionState(option_type="put", S=S, K=long_strike, T=T, r=r, sigma=iv, q=q),
    )

    return Position(name="bull_put_spread", legs=[short_put, long_put], opened_at=date)


def create_bear_call_spread(
    date: str,
    S: float,
    iv: float,
    dte_days: int = 45,
    r: float = 0.03,
    quantity: int = 1,
    q: float = 0.0,
    target_delta_short: float = 0.16,
    target_delta_long: float = 0.05,
) -> Position:
    T = dte_days / 365.0

    short_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_short, "call")
    long_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_long, "call")

    short_call = OptionLeg(
        sign=-1,
        quantity=quantity,
        state=OptionState(option_type="call", S=S, K=short_strike, T=T, r=r, sigma=iv, q=q),
    )
    long_call = OptionLeg(
        sign=+1,
        quantity=quantity,
        state=OptionState(option_type="call", S=S, K=long_strike, T=T, r=r, sigma=iv, q=q),
    )

    return Position(name="bear_call_spread", legs=[short_call, long_call], opened_at=date)


def create_put_broken_wing_butterfly(
    date: str,
    S: float,
    iv: float,
    dte_days: int = 45,
    r: float = 0.03,
    quantity: int = 1,
    q: float = 0.0,
    target_delta_short: float = 0.16,
    target_delta_long: float = 0.05,
) -> Position:
    """
    Put broken wing butterfly: long put OTM basso, 2x short put mid, long put ATM alto.
    target_delta_short → strike medio (2x short)
    target_delta_long  → strike basso (long protezione)
    Strike alto: calcolato come short + (short - low) per asimmetria broken wing.
    """
    T = dte_days / 365.0

    mid_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_short, "put")
    low_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_long, "put")
    # broken wing: il lato upside è più stretto del lato downside
    high_strike = round(mid_strike + (mid_strike - low_strike) * 0.5, 2)

    long_put_low = OptionLeg(
        sign=+1, quantity=quantity,
        state=OptionState(option_type="put", S=S, K=low_strike, T=T, r=r, sigma=iv, q=q),
    )
    short_put_1 = OptionLeg(
        sign=-1, quantity=quantity,
        state=OptionState(option_type="put", S=S, K=mid_strike, T=T, r=r, sigma=iv, q=q),
    )
    short_put_2 = OptionLeg(
        sign=-1, quantity=quantity,
        state=OptionState(option_type="put", S=S, K=mid_strike, T=T, r=r, sigma=iv, q=q),
    )
    long_put_high = OptionLeg(
        sign=+1, quantity=quantity,
        state=OptionState(option_type="put", S=S, K=high_strike, T=T, r=r, sigma=iv, q=q),
    )

    return Position(
        name="put_broken_wing_butterfly",
        legs=[long_put_low, short_put_1, short_put_2, long_put_high],
        opened_at=date,
    )
