import pytest
from app.engines.option.trade_decision import (
    TradeAction,
    TradeDecision,
    make_trade_decision,
)
from app.engines.option.opportunity_evaluator import (
    OpportunityEvaluation,
)


class TestTradeActionEnum:
    """Unit tests for TradeAction enum."""

    def test_trade_action_open(self):
        """TradeAction.OPEN is defined."""
        assert TradeAction.OPEN.value == "OPEN"

    def test_trade_action_monitor(self):
        """TradeAction.MONITOR is defined."""
        assert TradeAction.MONITOR.value == "MONITOR"

    def test_trade_action_skip(self):
        """TradeAction.SKIP is defined."""
        assert TradeAction.SKIP.value == "SKIP"


class TestTradeDecisionDataclass:
    """Unit tests for TradeDecision dataclass."""

    def test_trade_decision_creation(self):
        """TradeDecision can be created with all fields."""
        decision = TradeDecision(
            action=TradeAction.OPEN,
            score=85.0,
            reasoning="High confidence",
            threshold_open=75.0,
            threshold_skip=60.0,
        )
        assert decision.action == TradeAction.OPEN
        assert decision.score == 85.0
        assert decision.threshold_open == 75.0

    def test_trade_decision_monitor(self):
        """TradeDecision can be created with MONITOR action."""
        decision = TradeDecision(
            action=TradeAction.MONITOR,
            score=70.0,
            reasoning="Moderate confidence",
            threshold_open=75.0,
            threshold_skip=60.0,
        )
        assert decision.action == TradeAction.MONITOR

    def test_trade_decision_skip(self):
        """TradeDecision can be created with SKIP action."""
        decision = TradeDecision(
            action=TradeAction.SKIP,
            score=50.0,
            reasoning="Low confidence",
            threshold_open=75.0,
            threshold_skip=60.0,
        )
        assert decision.action == TradeAction.SKIP


class TestTradeDecisionOpen:
    """Unit tests for OPEN decision logic."""

    def test_open_score_high(self):
        """Score > threshold_open → OPEN."""
        eval = _create_opportunity_evaluation(composite_score=85.0)
        decision = make_trade_decision(eval)
        assert decision.action == TradeAction.OPEN
        assert decision.reasoning.startswith("High confidence")

    def test_open_score_very_high(self):
        """Score = 100 → OPEN."""
        eval = _create_opportunity_evaluation(composite_score=100.0)
        decision = make_trade_decision(eval)
        assert decision.action == TradeAction.OPEN

    def test_open_score_just_above_threshold(self):
        """Score = 75.1 → OPEN."""
        eval = _create_opportunity_evaluation(composite_score=75.1)
        decision = make_trade_decision(eval)
        assert decision.action == TradeAction.OPEN

    def test_open_reason_includes_score(self):
        """OPEN reasoning includes score and threshold."""
        eval = _create_opportunity_evaluation(composite_score=90.0)
        decision = make_trade_decision(eval)
        assert "90" in decision.reasoning
        assert "75" in decision.reasoning


class TestTradeDecisionMonitor:
    """Unit tests for MONITOR decision logic."""

    def test_monitor_score_middle(self):
        """60 ≤ Score ≤ 75 → MONITOR."""
        eval = _create_opportunity_evaluation(composite_score=70.0)
        decision = make_trade_decision(eval)
        assert decision.action == TradeAction.MONITOR
        assert decision.reasoning.startswith("Moderate confidence")

    def test_monitor_score_at_lower_bound(self):
        """Score = 60 → MONITOR."""
        eval = _create_opportunity_evaluation(composite_score=60.0)
        decision = make_trade_decision(eval)
        assert decision.action == TradeAction.MONITOR

    def test_monitor_score_at_upper_bound(self):
        """Score = 75 → MONITOR (inclusive lower, exclusive upper)."""
        eval = _create_opportunity_evaluation(composite_score=75.0)
        decision = make_trade_decision(eval)
        # At threshold_open, should be MONITOR, not OPEN (only > threshold_open is OPEN)
        assert decision.action == TradeAction.MONITOR

    def test_monitor_score_just_above_skip(self):
        """Score = 60.1 → MONITOR."""
        eval = _create_opportunity_evaluation(composite_score=60.1)
        decision = make_trade_decision(eval)
        assert decision.action == TradeAction.MONITOR

    def test_monitor_score_just_below_open(self):
        """Score = 74.9 → MONITOR."""
        eval = _create_opportunity_evaluation(composite_score=74.9)
        decision = make_trade_decision(eval)
        assert decision.action == TradeAction.MONITOR

    def test_monitor_reason_includes_thresholds(self):
        """MONITOR reasoning includes score and thresholds."""
        eval = _create_opportunity_evaluation(composite_score=68.0)
        decision = make_trade_decision(eval)
        assert "68" in decision.reasoning
        assert "60" in decision.reasoning
        assert "75" in decision.reasoning


class TestTradeDecisionSkip:
    """Unit tests for SKIP decision logic."""

    def test_skip_score_low(self):
        """Score < threshold_skip → SKIP."""
        eval = _create_opportunity_evaluation(composite_score=50.0)
        decision = make_trade_decision(eval)
        assert decision.action == TradeAction.SKIP
        assert decision.reasoning.startswith("Low confidence")

    def test_skip_score_zero(self):
        """Score = 0 → SKIP."""
        eval = _create_opportunity_evaluation(composite_score=0.0)
        decision = make_trade_decision(eval)
        assert decision.action == TradeAction.SKIP

    def test_skip_score_just_below_threshold(self):
        """Score = 59.9 → SKIP."""
        eval = _create_opportunity_evaluation(composite_score=59.9)
        decision = make_trade_decision(eval)
        assert decision.action == TradeAction.SKIP

    def test_skip_reason_includes_score(self):
        """SKIP reasoning includes score and threshold."""
        eval = _create_opportunity_evaluation(composite_score=45.0)
        decision = make_trade_decision(eval)
        assert "45" in decision.reasoning
        assert "60" in decision.reasoning


class TestCustomThresholds:
    """Unit tests for custom threshold configuration."""

    def test_custom_threshold_open(self):
        """Custom decision_threshold_open."""
        eval = _create_opportunity_evaluation(composite_score=80.0)
        decision = make_trade_decision(
            eval,
            position_config={"decision_threshold_open": 85.0}
        )
        # 80 < 85, so MONITOR not OPEN
        assert decision.action == TradeAction.MONITOR
        assert decision.threshold_open == 85.0

    def test_custom_threshold_skip(self):
        """Custom decision_threshold_skip."""
        eval = _create_opportunity_evaluation(composite_score=55.0)
        decision = make_trade_decision(
            eval,
            position_config={"decision_threshold_skip": 50.0}
        )
        # 55 >= 50, so MONITOR not SKIP
        assert decision.action == TradeAction.MONITOR
        assert decision.threshold_skip == 50.0

    def test_custom_both_thresholds(self):
        """Custom both thresholds."""
        eval = _create_opportunity_evaluation(composite_score=85.0)
        decision = make_trade_decision(
            eval,
            position_config={
                "decision_threshold_open": 80.0,
                "decision_threshold_skip": 50.0,
            }
        )
        assert decision.action == TradeAction.OPEN
        assert decision.threshold_open == 80.0
        assert decision.threshold_skip == 50.0

    def test_invalid_thresholds_open_less_than_skip(self):
        """Invalid: threshold_open <= threshold_skip → reset to defaults."""
        eval = _create_opportunity_evaluation(composite_score=70.0)
        decision = make_trade_decision(
            eval,
            position_config={
                "decision_threshold_open": 50.0,
                "decision_threshold_skip": 60.0,  # open < skip
            }
        )
        # Should reset to defaults: 75, 60
        assert decision.threshold_open == 75.0
        assert decision.threshold_skip == 60.0
        assert decision.action == TradeAction.MONITOR  # 70 < 75


class TestEdgeCases:
    """Unit tests for edge cases."""

    def test_score_exactly_at_open_threshold(self):
        """Score exactly at threshold_open → not OPEN (requires >)."""
        eval = _create_opportunity_evaluation(composite_score=75.0)
        decision = make_trade_decision(eval)
        assert decision.action == TradeAction.MONITOR
        assert decision.score == 75.0

    def test_score_exactly_at_skip_threshold(self):
        """Score exactly at threshold_skip → MONITOR (≥)."""
        eval = _create_opportunity_evaluation(composite_score=60.0)
        decision = make_trade_decision(eval)
        assert decision.action == TradeAction.MONITOR

    def test_empty_position_config(self):
        """Empty position_config → use defaults."""
        eval = _create_opportunity_evaluation(composite_score=80.0)
        decision = make_trade_decision(eval, position_config={})
        assert decision.threshold_open == 75.0
        assert decision.threshold_skip == 60.0
        assert decision.action == TradeAction.OPEN

    def test_none_position_config(self):
        """None position_config → use defaults."""
        eval = _create_opportunity_evaluation(composite_score=65.0)
        decision = make_trade_decision(eval, position_config=None)
        assert decision.threshold_open == 75.0
        assert decision.threshold_skip == 60.0
        assert decision.action == TradeAction.MONITOR


class TestFullPipelineL1toL5:
    """Unit tests for full L1→L5 pipeline."""

    def test_pipeline_high_score_to_open(self):
        """High OpportunityEvaluation score → TradeDecision.OPEN."""
        eval = OpportunityEvaluation(
            strategy_name="test_strategy",
            pricing_edge_score=90.0,
            risk_reward_score=85.0,
            breakeven_score=80.0,
            execution_cost_score=100.0,
            capital_efficiency_score=80.0,
            composite_score=87.5,
            edge_pct=0.50,
            risk_reward_ratio=2.5,
            breakeven_sigmas=0.5,
        )
        decision = make_trade_decision(eval)
        assert decision.action == TradeAction.OPEN
        assert decision.score == 87.5

    def test_pipeline_medium_score_to_monitor(self):
        """Medium OpportunityEvaluation score → TradeDecision.MONITOR."""
        eval = OpportunityEvaluation(
            strategy_name="test_strategy",
            pricing_edge_score=65.0,
            risk_reward_score=70.0,
            breakeven_score=65.0,
            execution_cost_score=70.0,
            capital_efficiency_score=65.0,
            composite_score=67.0,
            edge_pct=0.15,
            risk_reward_ratio=1.2,
            breakeven_sigmas=1.5,
        )
        decision = make_trade_decision(eval)
        assert decision.action == TradeAction.MONITOR
        assert decision.score == 67.0

    def test_pipeline_low_score_to_skip(self):
        """Low OpportunityEvaluation score → TradeDecision.SKIP."""
        eval = OpportunityEvaluation(
            strategy_name="test_strategy",
            pricing_edge_score=30.0,
            risk_reward_score=20.0,
            breakeven_score=25.0,
            execution_cost_score=40.0,
            capital_efficiency_score=30.0,
            composite_score=28.5,
            edge_pct=0.05,
            risk_reward_ratio=0.5,
            breakeven_sigmas=4.0,
        )
        decision = make_trade_decision(eval)
        assert decision.action == TradeAction.SKIP
        assert decision.score == 28.5


# Helper function
def _create_opportunity_evaluation(
    strategy_name: str = "test_strategy",
    composite_score: float = 70.0,
) -> OpportunityEvaluation:
    """Create test OpportunityEvaluation with custom composite_score."""
    return OpportunityEvaluation(
        strategy_name=strategy_name,
        pricing_edge_score=70.0,
        risk_reward_score=70.0,
        breakeven_score=70.0,
        execution_cost_score=70.0,
        capital_efficiency_score=70.0,
        composite_score=composite_score,
        edge_pct=0.20,
        risk_reward_ratio=1.5,
        breakeven_sigmas=1.0,
    )
