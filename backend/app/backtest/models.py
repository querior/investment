from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
from app.backtest.option.pricing import OptionState, black_scholes_greeks, black_scholes_price

CONTRACT_MULTIPLIER = 100

@dataclass
class OptionLeg:
    sign: int                 # +1 long, -1 short
    quantity: int             # numero contratti
    state: OptionState

    def price(self) -> float:
        return self.sign * self.quantity * black_scholes_price(self.state) * CONTRACT_MULTIPLIER

    def delta(self) -> float:
        g = black_scholes_greeks(self.state)
        return self.sign * self.quantity * g.delta * CONTRACT_MULTIPLIER

    def gamma(self) -> float:
        g = black_scholes_greeks(self.state)
        return self.sign * self.quantity * g.gamma * CONTRACT_MULTIPLIER

    def theta(self) -> float:
        g = black_scholes_greeks(self.state)
        return self.sign * self.quantity * g.theta_daily * CONTRACT_MULTIPLIER

    def vega(self) -> float:
        g = black_scholes_greeks(self.state)
        return self.sign * self.quantity * g.vega_per_iv_point * CONTRACT_MULTIPLIER


@dataclass
class Position:
  name: str
  legs: List[OptionLeg]
  opened_at: str
  initial_value: float = 0.0
  is_open: bool = True
    
  @property
  def price(self):
    return sum(leg.price() for leg in self.legs)
  
  @property
  def delta(self) -> float:
    return sum(leg.delta() for leg in self.legs)

  @property
  def gamma(self) -> float:
    return sum(leg.gamma() for leg in self.legs)

  @property
  def theta(self) -> float:
    return sum(leg.theta() for leg in self.legs)

  @property
  def vega(self) -> float:
    return sum(leg.vega() for leg in self.legs)

  @property
  def pnl(self) -> float:
    return self.price - self.initial_value

  def update_market(self, S: float, sigma: float, dt_years: float) -> None:
    for leg in self.legs:
      new_T = max(leg.state.T - dt_years, 1e-6)
      leg.state = OptionState(
          option_type=leg.state.option_type,
          S=S,
          K=leg.state.K,
          T=new_T,
          r=leg.state.r,
          sigma=sigma,
      )

@dataclass
class PortfolioSnapshot:
  date: str
  cash: float
  positions_value: float
  total_equity: float
  total_delta: float
  total_gamma: float
  total_theta: float
  total_vega: float

@dataclass
class Portfolio:
  
  initial_cash: float
  cash: float = field(init=False)
  positions: List[Position] = field(default_factory=list)
  history: List[PortfolioSnapshot] = field(default_factory=list)
  
  def __post_init__(self) -> None:
    self.cash = self.initial_cash
    
  def open_position(self, position: Position) -> None:
    position.initial_value = position.price
    self.cash -= position.initial_value
    self.positions.append(position)

  def close_position(self, position: Position) -> None:
    if not position.is_open:
        return
    self.cash += position.price
    position.is_open = False

  def remove_closed_positions(self) -> None:
    self.positions = [p for p in self.positions if p.is_open]

  def positions_value(self) -> float:
    return sum(p.price for p in self.positions if p.is_open)
  
  @property
  def total_equity(self) -> float:
      return self.cash + self.positions_value()

  @property
  def total_delta(self) -> float:
    return sum(p.delta for p in self.positions if p.is_open)

  @property
  def total_gamma(self) -> float:
      return sum(p.gamma for p in self.positions if p.is_open)

  @property
  def total_theta(self) -> float:
      return sum(p.theta for p in self.positions if p.is_open)

  @property
  def total_vega(self) -> float:
    return sum(p.vega for p in self.positions if p.is_open)
  
  