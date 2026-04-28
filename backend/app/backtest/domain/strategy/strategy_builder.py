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


# FAMIGLIA 1 — Debit Spreads (Zone A: Directional + Low IV)


def create_bull_call_spread(
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

    long_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_long, "call")
    short_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_short, "call")

    long_call = OptionLeg(
        sign=+1,
        quantity=quantity,
        state=OptionState(option_type="call", S=S, K=long_strike, T=T, r=r, sigma=iv, q=q),
    )
    short_call = OptionLeg(
        sign=-1,
        quantity=quantity,
        state=OptionState(option_type="call", S=S, K=short_strike, T=T, r=r, sigma=iv, q=q),
    )

    return Position(name="bull_call_spread", legs=[long_call, short_call], opened_at=date)


def create_bear_put_spread(
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

    return Position(name="bear_put_spread", legs=[short_put, long_put], opened_at=date)


# FAMIGLIA 3 — Long Volatility (Zone C: Lateral + Low IV)


def create_long_straddle(
    date: str,
    S: float,
    iv: float,
    dte_days: int = 45,
    r: float = 0.03,
    quantity: int = 1,
    q: float = 0.0,
) -> Position:
    T = dte_days / 365.0
    atm_strike = round(S, 2)

    long_call = OptionLeg(
        sign=+1,
        quantity=quantity,
        state=OptionState(option_type="call", S=S, K=atm_strike, T=T, r=r, sigma=iv, q=q),
    )
    long_put = OptionLeg(
        sign=+1,
        quantity=quantity,
        state=OptionState(option_type="put", S=S, K=atm_strike, T=T, r=r, sigma=iv, q=q),
    )

    return Position(name="long_straddle", legs=[long_call, long_put], opened_at=date)


def create_long_strangle(
    date: str,
    S: float,
    iv: float,
    dte_days: int = 45,
    r: float = 0.03,
    quantity: int = 1,
    q: float = 0.0,
    target_delta: float = 0.25,
) -> Position:
    T = dte_days / 365.0

    call_strike = find_strike_by_delta(S, T, r, q, iv, target_delta, "call")
    put_strike = find_strike_by_delta(S, T, r, q, iv, target_delta, "put")

    long_call = OptionLeg(
        sign=+1,
        quantity=quantity,
        state=OptionState(option_type="call", S=S, K=call_strike, T=T, r=r, sigma=iv, q=q),
    )
    long_put = OptionLeg(
        sign=+1,
        quantity=quantity,
        state=OptionState(option_type="put", S=S, K=put_strike, T=T, r=r, sigma=iv, q=q),
    )

    return Position(name="long_strangle", legs=[long_call, long_put], opened_at=date)


# FAMIGLIA 4 — Combined Spreads (Zone D: Lateral + High IV)


def create_iron_condor(
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

    put_short_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_short, "put")
    put_long_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_long, "put")
    call_short_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_short, "call")
    call_long_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_long, "call")

    short_put = OptionLeg(
        sign=-1,
        quantity=quantity,
        state=OptionState(option_type="put", S=S, K=put_short_strike, T=T, r=r, sigma=iv, q=q),
    )
    long_put = OptionLeg(
        sign=+1,
        quantity=quantity,
        state=OptionState(option_type="put", S=S, K=put_long_strike, T=T, r=r, sigma=iv, q=q),
    )
    short_call = OptionLeg(
        sign=-1,
        quantity=quantity,
        state=OptionState(option_type="call", S=S, K=call_short_strike, T=T, r=r, sigma=iv, q=q),
    )
    long_call = OptionLeg(
        sign=+1,
        quantity=quantity,
        state=OptionState(option_type="call", S=S, K=call_long_strike, T=T, r=r, sigma=iv, q=q),
    )

    return Position(
        name="iron_condor",
        legs=[short_put, long_put, short_call, long_call],
        opened_at=date,
    )


def create_iron_butterfly(
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
    atm_strike = round(S, 2)

    call_long_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_long, "call")
    put_long_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_long, "put")

    short_call = OptionLeg(
        sign=-1,
        quantity=quantity,
        state=OptionState(option_type="call", S=S, K=atm_strike, T=T, r=r, sigma=iv, q=q),
    )
    short_put = OptionLeg(
        sign=-1,
        quantity=quantity,
        state=OptionState(option_type="put", S=S, K=atm_strike, T=T, r=r, sigma=iv, q=q),
    )
    long_call = OptionLeg(
        sign=+1,
        quantity=quantity,
        state=OptionState(option_type="call", S=S, K=call_long_strike, T=T, r=r, sigma=iv, q=q),
    )
    long_put = OptionLeg(
        sign=+1,
        quantity=quantity,
        state=OptionState(option_type="put", S=S, K=put_long_strike, T=T, r=r, sigma=iv, q=q),
    )

    return Position(
        name="iron_butterfly",
        legs=[short_call, short_put, long_call, long_put],
        opened_at=date,
    )


# FAMIGLIA 5 — Advanced (Theta + Vol)


def create_calendar_spread(
    date: str,
    S: float,
    iv: float,
    dte_days: int = 45,
    r: float = 0.03,
    quantity: int = 1,
    q: float = 0.0,
    dte_days_near: int = 30,
    dte_days_far: int = 60,
    target_delta_short: float = 0.50,
) -> Position:
    T_near = dte_days_near / 365.0
    T_far = dte_days_far / 365.0
    atm_strike = round(S, 2)

    short_call = OptionLeg(
        sign=-1,
        quantity=quantity,
        state=OptionState(option_type="call", S=S, K=atm_strike, T=T_near, r=r, sigma=iv, q=q),
    )
    long_call = OptionLeg(
        sign=+1,
        quantity=quantity,
        state=OptionState(option_type="call", S=S, K=atm_strike, T=T_far, r=r, sigma=iv, q=q),
    )

    return Position(name="calendar_spread", legs=[short_call, long_call], opened_at=date)


def create_jade_lizard(
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

    put_short_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_short, "put")
    call_short_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_short, "call")
    call_long_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_long, "call")

    short_put = OptionLeg(
        sign=-1,
        quantity=quantity,
        state=OptionState(option_type="put", S=S, K=put_short_strike, T=T, r=r, sigma=iv, q=q),
    )
    short_call = OptionLeg(
        sign=-1,
        quantity=quantity,
        state=OptionState(option_type="call", S=S, K=call_short_strike, T=T, r=r, sigma=iv, q=q),
    )
    long_call = OptionLeg(
        sign=+1,
        quantity=quantity,
        state=OptionState(option_type="call", S=S, K=call_long_strike, T=T, r=r, sigma=iv, q=q),
    )

    return Position(name="jade_lizard", legs=[short_put, short_call, long_call], opened_at=date)


def create_reverse_jade_lizard(
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

    call_short_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_short, "call")
    put_short_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_short, "put")
    put_long_strike = find_strike_by_delta(S, T, r, q, iv, target_delta_long, "put")

    short_call = OptionLeg(
        sign=-1,
        quantity=quantity,
        state=OptionState(option_type="call", S=S, K=call_short_strike, T=T, r=r, sigma=iv, q=q),
    )
    short_put = OptionLeg(
        sign=-1,
        quantity=quantity,
        state=OptionState(option_type="put", S=S, K=put_short_strike, T=T, r=r, sigma=iv, q=q),
    )
    long_put = OptionLeg(
        sign=+1,
        quantity=quantity,
        state=OptionState(option_type="put", S=S, K=put_long_strike, T=T, r=r, sigma=iv, q=q),
    )

    return Position(
        name="reverse_jade_lizard",
        legs=[short_call, short_put, long_put],
        opened_at=date,
    )


def create_diagonal_spread(
    date: str,
    S: float,
    iv: float,
    dte_days: int = 45,
    r: float = 0.03,
    quantity: int = 1,
    q: float = 0.0,
    dte_days_near: int = 30,
    dte_days_far: int = 60,
    target_delta_short: float = 0.50,
    target_delta_long: float = 0.25,
) -> Position:
    T_near = dte_days_near / 365.0
    T_far = dte_days_far / 365.0

    short_strike = find_strike_by_delta(S, T_near, r, q, iv, target_delta_short, "call")
    long_strike = find_strike_by_delta(S, T_far, r, q, iv, target_delta_long, "call")

    short_call = OptionLeg(
        sign=-1,
        quantity=quantity,
        state=OptionState(option_type="call", S=S, K=short_strike, T=T_near, r=r, sigma=iv, q=q),
    )
    long_call = OptionLeg(
        sign=+1,
        quantity=quantity,
        state=OptionState(option_type="call", S=S, K=long_strike, T=T_far, r=r, sigma=iv, q=q),
    )

    return Position(name="diagonal_spread", legs=[short_call, long_call], opened_at=date)
