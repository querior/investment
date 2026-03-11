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

    return {
        "cagr": float(cagr),
        "volatility": float(volatility),
        "sharpe": float(sharpe),
        "max_drawdown": float(max_drawdown),
    }