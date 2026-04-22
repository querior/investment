from typing import Callable
from app.backtest.domain.strategy.exit_context import ExitContext

ExitRule = Callable[[ExitContext], bool]


def _cfg(ctx: ExitContext, rule: str) -> dict:
    """Legge la configurazione di una regola da ctx.exit_config con fallback a {}."""
    return ctx.exit_config.get(rule, {})


def rule_dte(ctx: ExitContext) -> bool:
    """Close at DTE threshold (default 21)."""
    cfg = _cfg(ctx, "rule_dte")
    if not cfg.get("enabled", True):
        return False
    threshold_days = float(cfg.get("threshold_days", 21))
    min_t = min(leg.state.T for leg in ctx.position.legs)
    return min_t <= threshold_days / 365.0


def rule_profit_target(ctx: ExitContext) -> bool:
    """Close when profit >= threshold % of initial credit (default 50%)."""
    cfg = _cfg(ctx, "rule_profit_target")
    if not cfg.get("enabled", True):
        return False
    threshold = float(cfg.get("threshold_pct", 50)) / 100
    pnl = ctx.position.price - ctx.position.initial_value
    return ctx.position.initial_value < 0 and pnl >= abs(ctx.position.initial_value) * threshold


def rule_stop_loss(ctx: ExitContext) -> bool:
    """Close when loss > threshold % of initial credit (default 200%)."""
    cfg = _cfg(ctx, "rule_stop_loss")
    if not cfg.get("enabled", True):
        return False
    threshold = float(cfg.get("threshold_pct", 200)) / 100
    pnl = ctx.position.price - ctx.position.initial_value
    return ctx.position.initial_value < 0 and pnl <= -abs(ctx.position.initial_value) * threshold


def rule_trailing_stop(ctx: ExitContext) -> bool:
    """Close when profit pulled back below pullback_pct after reaching min_profit_pct.
    Default: min_profit 30%, pullback 15%. Requires snapshot with max_pnl.
    """
    cfg = _cfg(ctx, "rule_trailing_stop")
    if not cfg.get("enabled", False):
        return False
    if ctx.snapshot is None:
        return False
    credit = abs(ctx.position.initial_value)
    pnl = ctx.position.price - ctx.position.initial_value
    max_pnl = getattr(ctx.snapshot, "max_pnl", None)
    if max_pnl is None:
        return False
    min_profit = float(cfg.get("min_profit_pct", 30)) / 100
    pullback = float(cfg.get("pullback_pct", 15)) / 100
    return max_pnl >= credit * min_profit and pnl < credit * pullback


def rule_macro_reversal(ctx: ExitContext) -> bool:
    """Close when macro regime is opposite to position direction."""
    cfg = _cfg(ctx, "rule_macro_reversal")
    if not cfg.get("enabled", True):
        return False
    regime = ctx.row.get("macro_regime")
    name = ctx.position.name
    if name == "bull_put_spread" and regime == "RISK_OFF":
        return True
    if name == "bear_call_spread" and regime == "RISK_ON":
        return True
    return False


def rule_momentum_reversal(ctx: ExitContext) -> bool:
    """Close when momentum signals are opposite to position direction."""
    cfg = _cfg(ctx, "rule_momentum_reversal")
    if not cfg.get("enabled", True):
        return False
    rsi = ctx.row.get("rsi_14")
    macd = ctx.row.get("macd")
    if rsi is None or macd is None:
        return False
    rsi_threshold = float(cfg.get("rsi_threshold", 30))
    use_macd = cfg.get("use_macd", True)
    name = ctx.position.name
    if name == "bull_put_spread":
        macd_cond = (macd < 0) if use_macd else True
        return rsi < rsi_threshold and macd_cond
    if name == "bear_call_spread":
        macd_cond = (macd > 0) if use_macd else True
        return rsi > (100 - rsi_threshold) and macd_cond
    return False


def rule_iv_spike(ctx: ExitContext) -> bool:
    """Close when IV/RV ratio exceeds threshold (default 2.0)."""
    cfg = _cfg(ctx, "rule_iv_spike")
    if not cfg.get("enabled", False):
        return False
    threshold = float(cfg.get("threshold_ratio", 2.0))
    iv_rv_ratio = ctx.row.get("iv_rv_ratio")
    if iv_rv_ratio is None:
        return False
    return float(iv_rv_ratio) > threshold


def rule_delta_breach(ctx: ExitContext) -> bool:
    """Close when |delta| exceeds threshold (default 0.50). Requires snapshot."""
    cfg = _cfg(ctx, "rule_delta_breach")
    if not cfg.get("enabled", False):
        return False
    if ctx.snapshot is None:
        return False
    delta = getattr(ctx.snapshot, "position_delta", None)
    if delta is None:
        return False
    threshold = float(cfg.get("threshold", 0.50))
    return abs(delta) > threshold


def rule_theta_decay(ctx: ExitContext) -> bool:
    """Close when |theta/price| exceeds threshold (default 0.05). Requires snapshot."""
    cfg = _cfg(ctx, "rule_theta_decay")
    if not cfg.get("enabled", False):
        return False
    if ctx.snapshot is None:
        return False
    theta = getattr(ctx.snapshot, "position_theta", None)
    price = ctx.position.price
    if theta is None or price == 0:
        return False
    threshold = float(cfg.get("threshold_ratio", 0.05))
    return abs(theta / price) > threshold


ALL_RULES: list[ExitRule] = [
    rule_dte,
    rule_profit_target,
    rule_stop_loss,
    rule_trailing_stop,
    rule_macro_reversal,
    rule_momentum_reversal,
    rule_iv_spike,
    rule_delta_breach,
    rule_theta_decay,
]


def should_close(ctx: ExitContext) -> tuple[bool, dict | None]:
    """
    Check if position should close and return reason if triggered.

    Returns:
        (should_close: bool, exit_conditions: dict | None)
    """
    for rule in ALL_RULES:
        if rule(ctx):
            rule_name = rule.__name__
            exit_conditions = _build_exit_conditions(rule_name, ctx)
            return True, exit_conditions

    return False, None


def _build_exit_conditions(triggered_rule: str, ctx: ExitContext) -> dict:
    """Build exit conditions with actual market data that triggered the exit."""
    pnl = ctx.position.price - ctx.position.initial_value
    credit = abs(ctx.position.initial_value)
    min_dte = min(leg.state.T for leg in ctx.position.legs)

    base_data = {
        "underlying_price": ctx.row.get("underlying_price"),
        "iv": ctx.row.get("iv"),
        "current_pnl": pnl,
        "pnl_pct": (pnl / credit * 100) if credit != 0 else 0,
        "dte": min_dte * 365,
    }

    # Add rule-specific data
    if triggered_rule == "rule_dte":
        return {
            "triggered_by": triggered_rule,
            "reason": f"DTE reached {min_dte * 365:.0f} days (≤21 threshold)",
            "data": {**base_data, "dte_threshold": 21},
        }

    elif triggered_rule == "rule_profit_target":
        return {
            "triggered_by": triggered_rule,
            "reason": f"Profit target reached: {pnl:.2f} ({pnl / credit * 100:.1f}% of credit)",
            "data": {**base_data, "profit_target_pct": 50},
        }

    elif triggered_rule == "rule_stop_loss":
        return {
            "triggered_by": triggered_rule,
            "reason": f"Stop loss triggered: {pnl:.2f} (>{200}% loss)",
            "data": {**base_data, "stop_loss_pct": 200},
        }

    elif triggered_rule == "rule_trailing_stop":
        max_pnl = getattr(ctx.snapshot, "max_pnl", None) if ctx.snapshot else None
        return {
            "triggered_by": triggered_rule,
            "reason": f"Trailing stop: max profit {max_pnl:.2f}, current {pnl:.2f}",
            "data": {**base_data, "max_pnl": max_pnl, "trailing_threshold_pct": 15},
        }

    elif triggered_rule == "rule_macro_reversal":
        return {
            "triggered_by": triggered_rule,
            "reason": f"Macro regime reversal to {ctx.row.get('macro_regime')}",
            "data": {**base_data, "macro_regime": ctx.row.get("macro_regime")},
        }

    elif triggered_rule == "rule_momentum_reversal":
        return {
            "triggered_by": triggered_rule,
            "reason": f"Momentum reversal: RSI {ctx.row.get('rsi_14'):.2f}, MACD {ctx.row.get('macd'):.4f}",
            "data": {
                **base_data,
                "rsi_14": ctx.row.get("rsi_14"),
                "macd": ctx.row.get("macd"),
            },
        }

    elif triggered_rule == "rule_iv_spike":
        iv_rv_ratio = ctx.row.get("iv_rv_ratio")
        return {
            "triggered_by": triggered_rule,
            "reason": f"IV spike: IV/RV ratio {iv_rv_ratio:.2f} (>2.0 threshold)",
            "data": {**base_data, "iv_rv_ratio": iv_rv_ratio, "iv_spike_threshold": 2.0},
        }

    elif triggered_rule == "rule_delta_breach":
        delta = getattr(ctx.snapshot, "position_delta", None) if ctx.snapshot else None
        return {
            "triggered_by": triggered_rule,
            "reason": f"Delta breach: {delta:.4f} (>{0.5} threshold)",
            "data": {**base_data, "position_delta": delta, "delta_threshold": 0.5},
        }

    elif triggered_rule == "rule_theta_decay":
        theta = getattr(ctx.snapshot, "position_theta", None) if ctx.snapshot else None
        theta_ratio = abs(theta / ctx.position.price) if theta is not None and ctx.position.price != 0 else 0
        return {
            "triggered_by": triggered_rule,
            "reason": f"Theta decay rate high: {theta_ratio:.2%}",
            "data": {**base_data, "position_theta": theta, "theta_ratio_threshold": 0.05},
        }

    return {"triggered_by": triggered_rule, "reason": "Unknown", "data": base_data}
