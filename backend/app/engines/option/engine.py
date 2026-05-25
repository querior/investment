"""
Option Decision Engine — Orchestrates L1→L5 decision pipeline.

Converts market signals into trade decisions for options strategies.
"""

import logging
import pandas as pd

from .models import Zone, Trend
from .zone_classifier import classify_zone
from .strategy_selector import select_strategy, calculate_position_size
from .pricing import calculate_pricing
from .opportunity_evaluator import evaluate_opportunity
from .trade_decision import make_trade_decision, TradeAction, TradeDecision
from app.backtest.domain.strategy import no_trade_strategy

logger = logging.getLogger(__name__)


class DecisionEngine:
    """
    Options Decision Engine — L1→L5 pipeline.

    Processes market signals and produces trade decisions (OPEN/MONITOR/SKIP)
    with detailed reasoning and scoring.
    """

    def process_signal(
        self,
        row: pd.Series | dict | None = None,
        entry_config: dict | None = None,
        position_config: dict | None = None,
        risk_config: dict | None = None,
    ) -> TradeDecision:
        """
        Process a market signal through all 5 decision levels.

        Args:
            row: Market data row with close, iv, dte_days, date, trend_signal, etc.
            entry_config: Entry configuration (thresholds, parameters)
            position_config: Position configuration (sizing, thresholds)
            risk_config: Risk configuration (max loss, bid/ask limits, etc.)

        Returns:
            TradeDecision with action (OPEN/MONITOR/SKIP) + score + reasoning
        """
        if row is None or entry_config is None or position_config is None:
            return self._create_skip_decision("Missing configuration")

        if risk_config is None:
            risk_config = {}

        zone_value: str | None = None
        try:
            # Level 1: Zone Classification
            iv_rank = row.get("iv_rank", 0.5)
            adx = row.get("adx", 20)
            zone = classify_zone(iv_rank, adx)
            zone_value = zone.value

            # Level 2: Strategy Selection
            trend_raw = row.get("trend_signal", Trend.NEUTRAL)
            trend = Trend(trend_raw) if isinstance(trend_raw, int) else trend_raw
            squeeze_intensity = row.get("squeeze_intensity", 0.5)
            entry_score = row.get("entry_score", 50.0)

            strategy_spec = select_strategy(
                zone=zone,
                trend=trend,
                squeeze_intensity=squeeze_intensity,
                iv_rank=iv_rank,
                adx=adx,
                trend_signal=trend_raw if isinstance(trend_raw, int) else trend.value,
                entry_score=entry_score,
            )

            # Level 3: Pricing & Greeks
            pricing = calculate_pricing(strategy_spec, row, entry_config)

            # No-trade strategy: zone known but no pricing/evaluation
            if pricing is None:
                decision = self._create_skip_decision("No-trade strategy selected")
                decision.zone = zone_value
                return decision

            # Level 4: Opportunity Evaluation
            evaluation = evaluate_opportunity(pricing, entry_config, risk_config)

            # Level 5: Trade Decision
            decision = make_trade_decision(evaluation, position_config)
            decision.edge_source = pricing.edge_source
            decision.zone = zone_value
            decision.evaluation = evaluation

            logger.warning(f"[ENGINE L5] action={decision.action.value}, score={decision.score:.1f}, edge_source={decision.edge_source}")

            # Attach strategy_spec to decision if action is OPEN
            if decision.action == TradeAction.OPEN:
                decision.strategy_spec = strategy_spec
                logger.warning(f"[ENGINE L5] Attached strategy_spec={strategy_spec.name if strategy_spec else None}")
            else:
                logger.warning(f"[ENGINE L5] action is not OPEN, strategy_spec remains None")

            return decision

        except Exception as e:
            decision = self._create_skip_decision(f"Pipeline error: {str(e)}")
            decision.zone = zone_value
            return decision

    def _create_skip_decision(self, reason: str) -> TradeDecision:
        """Create a SKIP decision with a given reason."""
        from .opportunity_evaluator import OpportunityEvaluation

        eval = OpportunityEvaluation(
            strategy_name="error_handler",
            pricing_edge_score=0.0,
            risk_reward_score=0.0,
            breakeven_score=0.0,
            execution_cost_score=0.0,
            capital_efficiency_score=0.0,
            composite_score=0.0,
            edge_pct=0.0,
            risk_reward_ratio=0.0,
            breakeven_sigmas=0.0,
        )
        decision = make_trade_decision(eval)
        decision.reasoning = reason
        return decision
