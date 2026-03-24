import math
import numpy as np


def compute_metrics(nav_series: list[float]) -> dict:
    if len(nav_series) < 2:
        return {}

    nav = np.array(nav_series)
    returns = nav[1:] / nav[:-1] - 1

    n_periods = len(returns)
    years = n_periods / 12

    cagr = (nav[-1] / nav[0]) ** (1 / years) - 1 if years > 0 else 0.0
    volatility = returns.std() * math.sqrt(12)
    sharpe = returns.mean() / returns.std() * math.sqrt(12) if returns.std() > 0 else 0.0

    running_max = np.maximum.accumulate(nav)
    drawdowns = nav / running_max - 1
    max_drawdown = drawdowns.min()

    wins = returns[returns > 0]
    losses = returns[returns < 0]
    win_rate = len(wins) / n_periods if n_periods > 0 else 0.0
    profit_factor = (wins.sum() / abs(losses.sum())) if len(losses) > 0 and losses.sum() != 0 else None

    return {
        "cagr": float(cagr),
        "volatility": float(volatility),
        "sharpe": float(sharpe),
        "max_drawdown": float(max_drawdown),
        "win_rate": float(win_rate),
        "profit_factor": float(profit_factor) if profit_factor is not None else None,
    }
