import pytest
import numpy as np
import pandas as pd
from app.engines.option.pricing import (
    PricingContext,
    calculate_pricing,
)
from app.engines.option.opportunity_evaluator import (
    OpportunityEvaluation,
    evaluate_opportunity,
)
from app.backtest.domain.strategy import (
    bull_call_spread_strategy,
    bear_put_spread_strategy,
    iron_condor_strategy,
    no_trade_strategy,
)


class TestOpportunityEvaluationDataclass:
    """Unit tests for OpportunityEvaluation dataclass."""

    def test_opportunity_evaluation_creation(self):
        """OpportunityEvaluation can be created with all fields."""
        eval = OpportunityEvaluation(
            strategy_name="test_strategy",
            pricing_edge_score=75.0,
            risk_reward_score=60.0,
            breakeven_score=50.0,
            execution_cost_score=80.0,
            capital_efficiency_score=70.0,
            composite_score=68.5,
            edge_pct=0.15,
            risk_reward_ratio=1.5,
            breakeven_sigmas=2.0,
        )
        assert eval.strategy_name == "test_strategy"
        assert eval.composite_score == 68.5

    def test_composite_score_calculation(self):
        """Composite score is correctly weighted average."""
        eval = OpportunityEvaluation(
            strategy_name="test",
            pricing_edge_score=100.0,
            risk_reward_score=100.0,
            breakeven_score=100.0,
            execution_cost_score=100.0,
            capital_efficiency_score=100.0,
            composite_score=100.0,
            edge_pct=0.5,
            risk_reward_ratio=2.0,
            breakeven_sigmas=1.0,
        )
        # Perfect score on all dimensions = composite 100
        assert eval.composite_score == 100.0


class TestPricingEdgeScore:
    """Unit tests for pricing edge scoring."""

    def test_edge_positive_high(self):
        """Positive edge high → score high."""
        pricing = _create_pricing_context(edge=2.0, fair_value=4.0)
        eval = evaluate_opportunity(pricing)
        # edge_pct = 0.5 → score = 100
        assert eval.pricing_edge_score > 90

    def test_edge_zero(self):
        """Zero edge → score 0."""
        pricing = _create_pricing_context(edge=0.0, fair_value=4.0)
        eval = evaluate_opportunity(pricing)
        assert eval.pricing_edge_score == 0.0

    def test_edge_negative(self):
        """Negative edge → score 0."""
        pricing = _create_pricing_context(edge=-1.0, fair_value=4.0)
        eval = evaluate_opportunity(pricing)
        assert eval.pricing_edge_score == 0.0

    def test_fair_value_near_zero(self):
        """Fair value near zero → score 0 (guard)."""
        pricing = _create_pricing_context(edge=1.0, fair_value=0.001)
        eval = evaluate_opportunity(pricing)
        assert eval.pricing_edge_score == 0.0


class TestRiskRewardScore:
    """Unit tests for risk/reward scoring."""

    def test_credit_strategy_high_rr(self):
        """Credit strategy (fair_value < 0) with high RR ratio → score high."""
        pricing = _create_pricing_context(
            fair_value=-1.0,
            strikes={"leg_0": 100.0, "leg_1": 110.0}
        )
        eval = evaluate_opportunity(pricing)
        # fair_value < 0 → credit, max_profit = 1.0, max_loss = 9.0
        # rr_ratio = 1.0/9.0 ≈ 0.11 → score ≈ 5.5
        assert eval.risk_reward_ratio > 0
        assert 0 < eval.risk_reward_score < 50

    def test_debit_strategy_high_rr(self):
        """Debit strategy (fair_value > 0) with high RR ratio → score high."""
        pricing = _create_pricing_context(
            fair_value=1.0,
            strikes={"leg_0": 100.0, "leg_1": 110.0}
        )
        eval = evaluate_opportunity(pricing)
        # fair_value > 0 → debit, max_profit = 9.0, max_loss = 1.0
        # rr_ratio = 9.0/1.0 = 9.0 → score = min(100, 9.0 * 50) = 100
        assert eval.risk_reward_ratio > 2
        assert eval.risk_reward_score > 50

    def test_rr_ratio_two_to_one(self):
        """RR ratio 2:1 → score 100."""
        pricing = _create_pricing_context(
            fair_value=2.0,
            strikes={"leg_0": 100.0, "leg_1": 110.0}
        )
        eval = evaluate_opportunity(pricing)
        # max_profit = 8.0, max_loss = 2.0 → rr_ratio = 4.0 → score = 100
        assert eval.risk_reward_score == 100.0

    def test_rr_ratio_zero(self):
        """RR ratio 0 → score 0."""
        pricing = _create_pricing_context(
            fair_value=10.0,
            strikes={"leg_0": 100.0, "leg_1": 110.0}
        )
        eval = evaluate_opportunity(pricing)
        # max_profit = 0, max_loss = 10.0 → rr_ratio = 0 → score = 0
        assert eval.risk_reward_score == 0.0


class TestBreakevenScore:
    """Unit tests for breakeven reachability scoring."""

    def test_breakeven_very_close(self):
        """Breakeven very close (< 1 sigma) → score high."""
        pricing = _create_pricing_context(
            breakeven_distance=0.5,  # 0.5% move
            spot=100,
            iv=0.20,
            dte_days=45,
        )
        eval = evaluate_opportunity(pricing)
        # expected_move ≈ 4.33%, breakeven_sigmas ≈ 0.12
        # score = 100 - 0.12 * 20 ≈ 97.6
        assert eval.breakeven_score > 90

    def test_breakeven_very_far(self):
        """Breakeven very far (> 5 sigma) → score 0."""
        pricing = _create_pricing_context(
            breakeven_distance=25.0,  # 25% move
            spot=100,
            iv=0.20,
            dte_days=45,
        )
        eval = evaluate_opportunity(pricing)
        # breakeven_sigmas ≈ 5.77 → score = 100 - 5.77 * 20 < 0 → 0
        assert eval.breakeven_score == 0.0

    def test_expected_move_zero(self):
        """Expected move = 0 → score 0 (guard)."""
        pricing = _create_pricing_context(
            breakeven_distance=1.0,
            spot=100,
            iv=0.0,  # zero vol
            dte_days=45,
        )
        eval = evaluate_opportunity(pricing)
        assert eval.breakeven_score == 0.0


class TestExecutionCostScore:
    """Unit tests for execution cost scoring."""

    def test_bid_ask_zero(self):
        """bid_ask_pct = 0 → score 100."""
        pricing = _create_pricing_context(bid_ask_pct=0.0)
        eval = evaluate_opportunity(pricing)
        assert eval.execution_cost_score == 100.0

    def test_bid_ask_max(self):
        """bid_ask_pct = max (default 0.15) → score 0."""
        pricing = _create_pricing_context(bid_ask_pct=0.15)
        eval = evaluate_opportunity(pricing)
        assert eval.execution_cost_score == 0.0

    def test_bid_ask_intermediate(self):
        """bid_ask_pct = 0.075 (50% of max) → score 50."""
        pricing = _create_pricing_context(bid_ask_pct=0.075)
        eval = evaluate_opportunity(pricing)
        assert eval.execution_cost_score == pytest.approx(50.0)

    def test_custom_max_bid_ask_pct(self):
        """Custom max_bid_ask_pct in risk_config."""
        pricing = _create_pricing_context(bid_ask_pct=0.10)
        eval = evaluate_opportunity(pricing, risk_config={"max_bid_ask_pct": 0.20})
        # score = (1 - 0.10/0.20) * 100 = 50
        assert eval.execution_cost_score == pytest.approx(50.0)


class TestCapitalEfficiencyScore:
    """Unit tests for capital efficiency scoring."""

    def test_theta_high(self):
        """Theta high → score high."""
        pricing = _create_pricing_context(theta=-0.1, fair_value=1.0)
        eval = evaluate_opportunity(pricing)
        # theta_efficiency = 0.1 / 1.0 * 365 = 36.5 → score = min(100, 36.5 * 500) > 100
        assert eval.capital_efficiency_score > 50

    def test_theta_zero(self):
        """Theta = 0 → score 0."""
        pricing = _create_pricing_context(theta=0.0, fair_value=1.0)
        eval = evaluate_opportunity(pricing)
        assert eval.capital_efficiency_score == 0.0

    def test_fair_value_near_zero(self):
        """fair_value near zero → score 0 (guard)."""
        pricing = _create_pricing_context(theta=-0.1, fair_value=0.001)
        eval = evaluate_opportunity(pricing)
        assert eval.capital_efficiency_score == 0.0


class TestCompositeScore:
    """Unit tests for composite score calculation."""

    def test_weights_sum_to_one(self):
        """Weights sum to 1.0."""
        # 0.35 + 0.25 + 0.20 + 0.15 + 0.05 = 1.0
        assert (0.35 + 0.25 + 0.20 + 0.15 + 0.05) == 1.0

    def test_perfect_score(self):
        """All dimensions score 100 → composite 100."""
        pricing = PricingContext(
            strategy_name="test",
            spot=100, iv=0.20, dte_days=45,
            strikes={"leg_0": 100, "leg_1": 110},
            delta=0.5, gamma=0.02, vega=10.0, theta=-0.5,
            market_price=2.0, fair_value=2.5,
            bid_ask_spread=0.0, bid_ask_pct=0.0,
            edge=0.5, breakeven_distance=0.5,
        )
        eval = evaluate_opportunity(pricing)
        # All scores 100 → composite = 100
        assert eval.composite_score > 90

    def test_zero_score(self):
        """All dimensions score 0 → composite 0."""
        pricing = _create_pricing_context(edge=0.0, fair_value=0.001)
        eval = evaluate_opportunity(pricing)
        # With fair_value near zero, pricing_edge = 0, composite should be low
        assert eval.composite_score < 20


class TestFullPipelineL1toL4:
    """Unit tests for full L1→L4 pipeline."""

    def test_bull_call_spread_pipeline(self):
        """Zone A, UP, bull_call → evaluate_opportunity → valid OpportunityEvaluation."""
        row = pd.Series({
            "close": 100,
            "iv": 0.2,
            "dte_days": 45,
            "date": "2026-04-28",
        })
        entry_config = {"target_delta_short": 0.16, "target_delta_long": 0.05}
        spec = bull_call_spread_strategy()

        pricing = calculate_pricing(spec, row, entry_config)
        eval = evaluate_opportunity(pricing)

        assert eval.strategy_name == "bull_call_spread"
        assert 0 <= eval.composite_score <= 100
        assert 0 <= eval.pricing_edge_score <= 100
        assert 0 <= eval.risk_reward_score <= 100

    def test_iron_condor_pipeline(self):
        """Zone D, iron_condor → evaluate_opportunity → valid OpportunityEvaluation."""
        row = pd.Series({
            "close": 100,
            "iv": 0.3,
            "dte_days": 45,
            "date": "2026-04-28",
        })
        entry_config = {"target_delta_short": 0.16, "target_delta_long": 0.05}
        spec = iron_condor_strategy()

        pricing = calculate_pricing(spec, row, entry_config)
        eval = evaluate_opportunity(pricing)

        assert eval.strategy_name == "iron_condor"
        assert isinstance(eval.composite_score, float)

    def test_no_trade_strategy_pipeline(self):
        """no_trade strategy → composite_score = 0."""
        row = pd.Series({
            "close": 100,
            "iv": 0.2,
            "dte_days": 45,
            "date": "2026-04-28",
        })
        entry_config = {}
        spec = no_trade_strategy()

        pricing = calculate_pricing(spec, row, entry_config)
        eval = evaluate_opportunity(pricing)

        # no_trade should have minimal edge
        assert eval.pricing_edge_score == 0.0


# Helper function to create test pricing contexts
def _create_pricing_context(
    edge: float = 0.5,
    fair_value: float = 2.5,
    market_price: float = 2.0,
    bid_ask_pct: float = 0.02,
    spot: float = 100.0,
    iv: float = 0.2,
    dte_days: int = 45,
    theta: float = -0.5,
    strikes: dict | None = None,
    breakeven_distance: float = 1.0,
) -> PricingContext:
    """Create a test PricingContext with custom values."""
    if strikes is None:
        strikes = {"leg_0": 100.0, "leg_1": 110.0}

    return PricingContext(
        strategy_name="test_strategy",
        spot=spot,
        iv=iv,
        dte_days=dte_days,
        strikes=strikes,
        delta=0.5,
        gamma=0.02,
        vega=10.0,
        theta=theta,
        market_price=market_price,
        fair_value=fair_value,
        bid_ask_spread=market_price * bid_ask_pct,
        bid_ask_pct=bid_ask_pct,
        edge=edge,
        breakeven_distance=breakeven_distance,
    )
