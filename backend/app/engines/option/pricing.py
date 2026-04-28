from dataclasses import dataclass
import numpy as np
import pandas as pd
from scipy.stats import norm

from app.backtest.domain.strategy.base import StrategySpec
from .greeks_calculator import calculate_delta, calculate_gamma, calculate_vega, calculate_theta


@dataclass
class PricingContext:
    """Aggregated pricing and Greeks for a multi-leg position."""

    strategy_name: str
    spot: float
    iv: float
    dte_days: int

    strikes: dict[str, float]

    delta: float
    gamma: float
    vega: float
    theta: float

    market_price: float
    fair_value: float
    bid_ask_spread: float
    bid_ask_pct: float

    edge: float
    breakeven_distance: float


def black_scholes(
    S: float, K: float, T: float, sigma: float, r: float, option_type: str
) -> float:
    """Black-Scholes option pricing formula."""
    if T <= 0:
        if option_type == "call":
            return max(S - K, 0)
        else:
            return max(K - S, 0)

    if sigma == 0:
        if option_type == "call":
            return max(S - K * np.exp(-r * T), 0)
        else:
            return max(K * np.exp(-r * T) - S, 0)

    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == "call":
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:  # put
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def calculate_pricing(
    spec: StrategySpec,
    row: pd.Series,
    entry_config: dict,
) -> PricingContext:
    """
    Calculate pricing and Greeks for a strategy position.

    Generic approach: builds position from spec, prices each leg via Black-Scholes,
    aggregates Greeks respecting position signs (+1 long, -1 short).

    Args:
        spec: StrategySpec from strategy_selector
        row: Market data row (close, iv, dte_days, date, etc)
        entry_config: Config dict with delta targets, pricing params

    Returns:
        PricingContext with fair_value, market_price, Greeks, edge
    """
    spot = row["close"]
    iv = row["iv"]
    dte_days = int(row.get("dte_days", 45))
    date = row["date"]

    target_delta_short = entry_config.get("target_delta_short", 0.16)
    target_delta_long = entry_config.get("target_delta_long", 0.05)

    # Build position from strategy spec
    # Some builders require delta targets, others don't (e.g. ATM straddle)
    # Try with delta targets first, fall back to minimal params if not supported
    try:
        position = spec.builder(
            date=date,
            S=spot,
            iv=iv,
            dte_days=dte_days,
            target_delta_short=target_delta_short,
            target_delta_long=target_delta_long,
            quantity=1,
        )
    except TypeError:
        # Builder doesn't accept delta targets (e.g., long straddle/strangle at ATM/OTM)
        position = spec.builder(
            date=date,
            S=spot,
            iv=iv,
            dte_days=dte_days,
            quantity=1,
        )

    # Price each leg and calculate Greeks
    total_delta = 0.0
    total_gamma = 0.0
    total_vega = 0.0
    total_theta = 0.0
    fair_value = 0.0

    for leg in position.legs:
        # Black-Scholes pricing for this leg
        leg_price = black_scholes(
            S=spot,
            K=leg.state.K,
            T=leg.state.T,
            sigma=iv,
            r=leg.state.r,
            option_type=leg.state.option_type,
        )

        # Greeks for this leg
        leg_delta = calculate_delta(
            K=leg.state.K,
            S=spot,
            sigma=iv,
            T=leg.state.T,
            option_type=leg.state.option_type,
        )
        leg_gamma = calculate_gamma(K=leg.state.K, S=spot, sigma=iv, T=leg.state.T)
        leg_vega = calculate_vega(K=leg.state.K, S=spot, sigma=iv, T=leg.state.T)
        leg_theta = calculate_theta(
            K=leg.state.K,
            S=spot,
            sigma=iv,
            T=leg.state.T,
            option_type=leg.state.option_type,
            r=leg.state.r,
        )

        # Aggregate with position sign (+1 long, -1 short)
        fair_value += leg_price * leg.sign
        total_delta += leg_delta * leg.sign
        total_gamma += leg_gamma * leg.sign
        total_vega += leg_vega * leg.sign
        total_theta += leg_theta * leg.sign

    # Market price (from row or fallback to fair value)
    market_price = row.get("market_price", fair_value)
    bid_ask_pct = row.get("bid_ask_pct", 0.02)
    bid_ask_spread = market_price * bid_ask_pct if market_price > 0 else 0

    # Edge: our profit if buy at market and sell at fair value
    edge = fair_value - market_price

    # Breakeven distance: % move from spot to breakeven
    if spot > 0 and abs(total_delta) > 0.01:
        breakeven_distance = (fair_value / spot) * 100
    else:
        breakeven_distance = 0.0

    # Extract strikes from position legs
    strikes = {f"leg_{i}": leg.state.K for i, leg in enumerate(position.legs)}

    return PricingContext(
        strategy_name=spec.name,
        spot=spot,
        iv=iv,
        dte_days=dte_days,
        strikes=strikes,
        delta=total_delta,
        gamma=total_gamma,
        vega=total_vega,
        theta=total_theta,
        market_price=market_price,
        fair_value=fair_value,
        bid_ask_spread=bid_ask_spread,
        bid_ask_pct=bid_ask_pct,
        edge=edge,
        breakeven_distance=breakeven_distance,
    )
