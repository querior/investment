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
    
def compute_run_eod_metrics(nav_series: list[float], return_series: list[float]) -> dict[str, float | int | None]:
    if not nav_series:
        return {
            "cagr": None,
            "volatility": None,
            "sharpe": None,
            "max_drawdown": None,
            "win_rate": None,
            "profit_factor": None,
            "n_trades": None,
        }

    nav = np.array(nav_series, dtype=float)
    rets = np.array(return_series[1:] if len(return_series) > 1 else [], dtype=float)
    # escludo il primo return artificiale = 0

    initial_nav = nav[0]
    final_nav = nav[-1]
    n_days = len(nav)

    cagr = None
    if initial_nav > 0 and final_nav > 0 and n_days > 1:
        years = n_days / 252.0
        if years > 0:
            cagr = (final_nav / initial_nav) ** (1 / years) - 1

    volatility = None
    sharpe = None
    if len(rets) > 1:
        daily_std = float(np.std(rets, ddof=1))
        daily_mean = float(np.mean(rets))

        volatility = daily_std * math.sqrt(252)

        if daily_std > 0:
            sharpe = (daily_mean / daily_std) * math.sqrt(252)

    running_max = np.maximum.accumulate(nav)
    drawdowns = (nav / running_max) - 1.0
    max_drawdown = float(np.min(drawdowns)) if len(drawdowns) else None

    win_rate = None
    if len(rets) > 0:
        wins = np.sum(rets > 0)
        win_rate = float(wins / len(rets))

    profit_factor = None
    if len(rets) > 0:
        gross_profit = float(np.sum(rets[rets > 0]))
        gross_loss = float(-np.sum(rets[rets < 0]))
        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss

    return {
        "cagr": cagr,
        "volatility": volatility,
        "sharpe": sharpe,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "n_trades": None,  # lo valorizzi a parte
    }
