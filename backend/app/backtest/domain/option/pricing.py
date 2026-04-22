from __future__ import annotations

from dataclasses import dataclass
from math import erf, exp, log, pi, sqrt


def norm_cdf(x: float) -> float:
  return 0.5 * (1.0 + erf(x / sqrt(2.0)))


def norm_pdf(x: float) -> float:
  return (1.0 / sqrt(2.0 * pi)) * exp(-0.5 * x * x)


@dataclass
class OptionState:
  option_type: str   # "call" o "put"
  S: float           # prezzo sottostante
  K: float           # strike
  T: float           # tempo a scadenza in anni
  r: float           # tasso risk-free annuale, es. 0.04
  sigma: float       # volatilità implicita annuale, es. 0.25
  q: float = 0.0     # dividend yield continuo (da InstrumentConfig)


@dataclass
class Greeks:
  delta: float
  gamma: float
  theta_daily: float
  vega_per_iv_point: float
  prob_itm: float    # N(d2) per call, N(-d2) per put


def _validate_inputs(state: OptionState) -> None:
  if state.option_type not in {"call", "put"}:
    raise ValueError("option_type deve essere 'call' oppure 'put'")
  if state.S <= 0:
    raise ValueError("S deve essere > 0")
  if state.K <= 0:
    raise ValueError("K deve essere > 0")
  if state.T <= 0:
    raise ValueError("T deve essere > 0")
  if state.sigma <= 0:
    raise ValueError("sigma deve essere > 0")


def _d1_d2(state: OptionState) -> tuple[float, float]:
  _validate_inputs(state)
  d1 = (
    log(state.S / state.K)
    + (state.r - state.q + 0.5 * state.sigma ** 2) * state.T
  ) / (state.sigma * sqrt(state.T))
  d2 = d1 - state.sigma * sqrt(state.T)
  return d1, d2


def black_scholes_price(state: OptionState) -> float:
  d1, d2 = _d1_d2(state)

  if state.option_type == "call":
    return (
      state.S * exp(-state.q * state.T) * norm_cdf(d1)
      - state.K * exp(-state.r * state.T) * norm_cdf(d2)
    )

  return (
    state.K * exp(-state.r * state.T) * norm_cdf(-d2)
    - state.S * exp(-state.q * state.T) * norm_cdf(-d1)
  )


def black_scholes_greeks(state: OptionState) -> Greeks:
  d1, d2 = _d1_d2(state)

  disc_q = exp(-state.q * state.T)
  disc_r = exp(-state.r * state.T)

  if state.option_type == "call":
    delta = disc_q * norm_cdf(d1)
    prob_itm = norm_cdf(d2)
    theta_annual = (
      -(state.S * disc_q * norm_pdf(d1) * state.sigma) / (2.0 * sqrt(state.T))
      + state.q * state.S * disc_q * norm_cdf(d1)
      - state.r * state.K * disc_r * norm_cdf(d2)
    )
  else:
    delta = disc_q * (norm_cdf(d1) - 1.0)
    prob_itm = norm_cdf(-d2)
    theta_annual = (
      -(state.S * disc_q * norm_pdf(d1) * state.sigma) / (2.0 * sqrt(state.T))
      - state.q * state.S * disc_q * norm_cdf(-d1)
      + state.r * state.K * disc_r * norm_cdf(-d2)
    )

  gamma = disc_q * norm_pdf(d1) / (state.S * state.sigma * sqrt(state.T))

  # vega classica per variazione di sigma in unità decimali
  vega = state.S * disc_q * norm_pdf(d1) * sqrt(state.T)

  # conversione pratica: prezzo per +1 punto di IV (es. 20% -> 21%)
  vega_per_iv_point = vega * 0.01

  # theta giornaliera
  theta_daily = theta_annual / 365.0

  return Greeks(
    delta=delta,
    gamma=gamma,
    theta_daily=theta_daily,
    vega_per_iv_point=vega_per_iv_point,
    prob_itm=prob_itm,
  )


def option_price_local_approx(
  current_price: float,
  dS: float,
  d_iv_points: float,
  dt_days: float,
  greeks: Greeks,
) -> float:
  """
  Approssimazione locale usando le greche nel punto iniziale.

  Formula:
  V ≈ V0 + Δ*dS + 0.5*Γ*dS^2 + Vega*dIV + Theta*dt
  """
  return (
    current_price
    + greeks.delta * dS
    + 0.5 * greeks.gamma * (dS ** 2)
    + greeks.vega_per_iv_point * d_iv_points
    + greeks.theta_daily * dt_days
  )


def scenario_reprice(
  state: OptionState,
  new_S: float | None = None,
  iv_shift_points: float = 0.0,
  days_forward: float = 0.0,
) -> dict:
  """
  Ricalcola prezzo e greche in un nuovo scenario.
  Più robusto della formula locale, perché aggiorna il modello.
  """
  new_sigma = state.sigma + iv_shift_points / 100.0
  new_T = max(state.T - days_forward / 365.0, 1e-6)

  new_state = OptionState(
    option_type=state.option_type,
    S=new_S if new_S is not None else state.S,
    K=state.K,
    T=new_T,
    r=state.r,
    sigma=new_sigma,
  )

  new_price = black_scholes_price(new_state)
  new_greeks = black_scholes_greeks(new_state)

  return {
    "state": new_state,
    "price": new_price,
    "greeks": new_greeks,
  }