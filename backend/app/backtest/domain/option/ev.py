from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.backtest.domain.option.pricing import OptionState, black_scholes_greeks, black_scholes_price

if TYPE_CHECKING:
    from app.backtest.domain.instrument import InstrumentConfig


@dataclass
class LegEV:
    strike: float
    option_type: str
    position: str   # "long" | "short"
    quantity: int
    fair_value: float
    prob_itm: float
    delta: float


@dataclass
class TradeEV:
    legs: list[LegEV]
    net_premium: float
    max_profit: float
    max_loss: float
    prob_profit: float
    expected_value_gross: float
    transaction_costs: float
    expected_value_net: float
    fair_value: float

    @property
    def has_edge(self) -> bool:
        """
        Con IV simulata questo è sempre False (premio = FV per costruzione).
        Diventa significativo solo con dati IV reali dove premio > FV.
        Usare is_credit per il filtro entry con IV simulata.
        """
        return self.expected_value_net > 0

    @property
    def is_credit(self) -> bool:
        """La struttura genera un credito netto. Filtro minimo per credit spreads."""
        return self.net_premium > 0


def compute_trade_ev(
    legs: list[dict],
    S: float,
    T: float,
    r: float,
    sigma: float,
    instrument: "InstrumentConfig",
) -> TradeEV:
    """
    Calcola Expected Value pre-trade per una struttura multi-leg.

    legs: lista di dict con chiavi { strike, type, position, qty }
          type: "call" | "put"
          position: "long" | "short"
    """
    q = instrument.dividend_yield
    multiplier = instrument.contract_multiplier

    leg_evs: list[LegEV] = []
    net_premium = 0.0
    total_fair_value = 0.0

    for leg in legs:
        state = OptionState(
            option_type=leg["type"],
            S=S,
            K=leg["strike"],
            T=T,
            r=r,
            sigma=sigma,
            q=q,
        )
        fv = black_scholes_price(state)
        greeks = black_scholes_greeks(state)

        sign = 1 if leg["position"] == "short" else -1
        net_premium += sign * fv * leg["qty"] * multiplier
        total_fair_value += fv * leg["qty"] * multiplier

        leg_evs.append(LegEV(
            strike=leg["strike"],
            option_type=leg["type"],
            position=leg["position"],
            quantity=leg["qty"],
            fair_value=fv,
            prob_itm=greeks.prob_itm,
            delta=greeks.delta,
        ))

    # Per credit spread: max_profit = credito netto, max_loss = spread_width - credito
    if len(legs) >= 2:
        spread_width = abs(legs[1]["strike"] - legs[0]["strike"]) * multiplier
    else:
        spread_width = 0.0

    max_profit = net_premium
    max_loss = spread_width - net_premium if spread_width > 0 else abs(net_premium)

    # PoP: prob che il sottostante resti fuori dallo short strike (per credit spread)
    short_legs = [l for l in leg_evs if l.position == "short"]
    if short_legs:
        pop = 1.0 - short_legs[0].prob_itm
    else:
        pop = 0.5

    ev_gross = pop * max_profit - (1.0 - pop) * max_loss

    n_contracts = sum(leg["qty"] for leg in legs)
    costs = instrument.cost_model.total_cost(net_premium, n_contracts)

    ev_net = ev_gross - costs

    return TradeEV(
        legs=leg_evs,
        net_premium=net_premium,
        max_profit=max_profit,
        max_loss=max_loss,
        prob_profit=pop,
        expected_value_gross=ev_gross,
        transaction_costs=costs,
        expected_value_net=ev_net,
        fair_value=total_fair_value,
    )
