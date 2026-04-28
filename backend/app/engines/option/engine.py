"""
Option Decision Engine — Orchestrates L1→L5 decision pipeline.

Converts market signals into trade decisions for options strategies.
"""

from .models import Zone, Trend
from .zone_classifier import classify_zone
from .strategy_selector import select_strategy, calculate_position_size
from .pricing import calculate_pricing
from .opportunity_evaluator import evaluate_opportunity
from .trade_decision import make_trade_decision, TradeAction, TradeDecision
from app.backtest.domain.strategy import no_trade_strategy


class DecisionEngine:
    """
    Options Decision Engine — L1→L5 pipeline.

    Processes market signals and produces trade decisions (OPEN/MONITOR/SKIP)
    with detailed reasoning and scoring.
    """

    def process_signal(
        self,
        row: dict | None = None,
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

        try:
            # Level 1: Zone Classification
            iv_rank = row.get("iv_rank", 0.5)
            adx = row.get("adx", 20)
            zone = classify_zone(iv_rank, adx)

            # Level 2: Strategy Selection
            trend = row.get("trend_signal", Trend.NEUTRAL)
            squeeze_intensity = row.get("squeeze_intensity", 0.5)
            entry_score = row.get("entry_score", 50.0)

            strategy_spec = select_strategy(
                zone=zone,
                trend=trend,
                squeeze_intensity=squeeze_intensity,
                iv_rank=iv_rank,
                entry_score=entry_score,
            )

            # Level 3: Pricing & Greeks
            pricing = calculate_pricing(strategy_spec, row, entry_config)

            # Level 4: Opportunity Evaluation
            evaluation = evaluate_opportunity(pricing, entry_config, risk_config)

            # Level 5: Trade Decision
            decision = make_trade_decision(evaluation, position_config)

            return decision

        except Exception as e:
            return self._create_skip_decision(f"Pipeline error: {str(e)}")

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
