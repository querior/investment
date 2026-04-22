import math
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


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


def compute_ev_accuracy(db: "Session", run_id: int) -> dict:
    """
    Confronta EV stimato all'entry con P&L realizzato sulle posizioni chiuse.

    Metriche:
    - n_positions: posizioni chiuse con dati EV
    - mean_ev_net: EV netto medio stimato all'entry
    - mean_realized_pnl: P&L medio realizzato
    - ev_accuracy: mean_realized_pnl / mean_ev_net (1.0 = perfetto)
    - actual_win_rate: % posizioni chiuse in profitto
    - mean_entry_prob_profit: PoP stimata media all'entry
    - pop_bias: actual_win_rate - mean_entry_prob_profit (bias della stima)
    - cost_drag: mean_transaction_costs / mean_abs_initial_value
    """
    from app.backtest.schemas.backtest_position import BacktestPosition

    rows = (
        db.query(BacktestPosition)
        .filter(
            BacktestPosition.run_id == run_id,
            BacktestPosition.status == "CLOSED",
            BacktestPosition.entry_ev_net.isnot(None),
        )
        .all()
    )

    n = len(rows)
    if n == 0:
        return {"n_positions": 0}

    ev_nets = [r.entry_ev_net for r in rows]
    realized_pnls = [r.realized_pnl for r in rows if r.realized_pnl is not None]
    prob_profits = [r.entry_prob_profit for r in rows if r.entry_prob_profit is not None]
    transaction_costs = [r.entry_transaction_costs for r in rows if r.entry_transaction_costs is not None]
    initial_values = [r.initial_value for r in rows]

    mean_ev_net = float(np.mean(ev_nets))
    mean_realized_pnl = float(np.mean(realized_pnls)) if realized_pnls else None
    actual_win_rate = float(np.mean([1 if p > 0 else 0 for p in realized_pnls])) if realized_pnls else None
    mean_entry_prob_profit = float(np.mean(prob_profits)) if prob_profits else None
    mean_transaction_costs = float(np.mean(transaction_costs)) if transaction_costs else None
    mean_abs_initial_value = float(np.mean([abs(v) for v in initial_values]))

    ev_accuracy = None
    if mean_realized_pnl is not None and mean_ev_net != 0:
        ev_accuracy = mean_realized_pnl / mean_ev_net

    pop_bias = None
    if actual_win_rate is not None and mean_entry_prob_profit is not None:
        pop_bias = actual_win_rate - mean_entry_prob_profit

    cost_drag = None
    if mean_transaction_costs is not None and mean_abs_initial_value != 0:
        cost_drag = mean_transaction_costs / mean_abs_initial_value

    return {
        "n_positions": n,
        "mean_ev_net": mean_ev_net,
        "mean_realized_pnl": mean_realized_pnl,
        "ev_accuracy": ev_accuracy,
        "actual_win_rate": actual_win_rate,
        "mean_entry_prob_profit": mean_entry_prob_profit,
        "pop_bias": pop_bias,
        "mean_transaction_costs": mean_transaction_costs,
        "cost_drag": cost_drag,
    }
