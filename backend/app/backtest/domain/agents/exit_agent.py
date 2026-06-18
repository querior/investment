from __future__ import annotations
from dataclasses import dataclass
from app.backtest.domain.agents.base import ExitSignal
from app.backtest.domain.strategy.exit_context import ExitContext
from app.backtest.domain.strategy.exit_rules import should_close
from app.backtest.domain.models import Position, Portfolio


@dataclass
class _PositionSnap:
    """Minimal snapshot proxy — provides max_pnl + greeks without DB access."""
    max_pnl: float
    position_delta: float
    position_theta: float


class ExitAgent:
    """
    Decides HOLD / CLOSE / ROLL for each open position.

    Priority:
    1. Portfolio trailing stop — CLOSE all if equity falls too far from peak
    2. Per-position exit rules — delegates to exit_rules.should_close
    3. Rollout — ROLL instead of CLOSE when DTE exit + rollout enabled + profitable

    This is the first ML-ready component: decide() is rule-based now,
    replaceable with a classifier when training data is available.
    """

    def __init__(
        self,
        exit_config: dict,
        strategy_overrides: dict | None = None,
        rollout_config: dict | None = None,
        portfolio_trailing_stop: dict | None = None,
    ):
        self._exit_config = exit_config
        self._strategy_overrides = strategy_overrides or {}
        self._rollout_config = rollout_config or {}
        self._pts = portfolio_trailing_stop or {}

        # State tracked across timesteps
        self._peak_equity: float = 0.0
        self._position_max_pnl: dict[int, float] = {}

    def update_portfolio_peak(self, equity: float) -> None:
        """Update the high-water mark. Must be called once per day before decide()."""
        if equity > self._peak_equity:
            self._peak_equity = equity

    def is_portfolio_stop_triggered(self, equity: float) -> bool:
        if not self._pts.get("enabled", False):
            return False
        if self._peak_equity <= 0:
            return False
        pullback = float(self._pts.get("pullback_pct", 20)) / 100
        return equity < self._peak_equity * (1 - pullback)

    def decide(self, position: Position, row, portfolio: Portfolio) -> ExitSignal:
        """Return HOLD / CLOSE / ROLL for a single open position."""

        # 1. Portfolio trailing stop — overrides all per-position rules
        if self.is_portfolio_stop_triggered(portfolio.total_equity):
            pullback = float(self._pts.get("pullback_pct", 20))
            floor = self._peak_equity * (1 - pullback / 100)
            return ExitSignal(
                action="CLOSE",
                reason=(
                    f"Portfolio trailing stop: equity {portfolio.total_equity:.2f} "
                    f"< floor {floor:.2f} (peak={self._peak_equity:.2f}, pullback={pullback:.0f}%)"
                ),
                triggered_by="portfolio_trailing_stop",
                exit_conditions={
                    "triggered_by": "portfolio_trailing_stop",
                    "peak_equity": self._peak_equity,
                    "current_equity": portfolio.total_equity,
                    "pullback_pct": pullback,
                },
            )

        # 2. Per-position exit rules
        pos_id = id(position)
        current_pnl = position.pnl
        self._position_max_pnl[pos_id] = max(
            self._position_max_pnl.get(pos_id, current_pnl),
            current_pnl,
        )

        # Provide greeks + max_pnl to rules that need them (trailing stop, delta breach, theta decay)
        snap = _PositionSnap(
            max_pnl=self._position_max_pnl[pos_id],
            position_delta=position.delta,
            position_theta=position.theta,
        )

        ctx = ExitContext(
            position=position,
            row=row,
            snapshot=snap,
            exit_config=self._build_pos_config(position),
        )
        should_exit, exit_conditions = should_close(ctx)

        if not should_exit:
            return ExitSignal(action="HOLD", reason="No exit rule triggered")

        triggered_by = (exit_conditions or {}).get("triggered_by", "unknown")

        # 3. Rollout: DTE exit + rollout enabled + position profitable enough
        if triggered_by == "rule_dte" and self._rollout_config.get("enabled"):
            min_pnl = (
                float(self._rollout_config.get("min_profit_pct", 0)) / 100.0
                * abs(position.initial_value)
            )
            if position.pnl >= min_pnl:
                return ExitSignal(
                    action="ROLL",
                    reason=(
                        f"DTE exit with pnl {position.pnl:.2f} >= min {min_pnl:.2f}, "
                        "rolling to next expiry"
                    ),
                    triggered_by=triggered_by,
                    exit_conditions=exit_conditions,
                )

        return ExitSignal(
            action="CLOSE",
            reason=(exit_conditions or {}).get("reason", "Exit rule triggered"),
            triggered_by=triggered_by,
            exit_conditions=exit_conditions,
        )

    def _build_pos_config(self, position: Position) -> dict:
        """Merge global exit config with per-strategy zone overrides."""
        entry_zone = getattr(position, "entry_zone", "")
        s_cfg = self._strategy_overrides.get(position.name, {}).get(entry_zone, {})
        merged = dict(self._exit_config)

        if s_cfg.get("profit_target_pct") is not None:
            merged["rule_profit_target"] = {
                **merged.get("rule_profit_target", {}),
                "threshold_pct": float(s_cfg["profit_target_pct"]),
                "enabled": True,
            }
        if s_cfg.get("stop_loss_pct") is not None:
            merged["rule_stop_loss"] = {
                **merged.get("rule_stop_loss", {}),
                "threshold_pct": float(s_cfg["stop_loss_pct"]),
                "enabled": True,
            }
        if s_cfg.get("dte_exit_days") is not None:
            merged["rule_dte"] = {
                **merged.get("rule_dte", {}),
                "threshold_days": float(s_cfg["dte_exit_days"]),
                "enabled": True,
            }
        return merged
