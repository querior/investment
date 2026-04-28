from dataclasses import dataclass
import numpy as np
from .pricing import PricingContext


@dataclass
class OpportunityEvaluation:
    """Multi-dimensional evaluation of a trade opportunity."""

    strategy_name: str

    # Scoring per dimensione (0-100 ciascuno)
    pricing_edge_score: float        # 35% weight
    risk_reward_score: float         # 25% weight
    breakeven_score: float           # 20% weight
    execution_cost_score: float      # 15% weight
    capital_efficiency_score: float  # 5% weight

    composite_score: float           # weighted sum (0-100)

    # Valori raw per debug/logging
    edge_pct: float                  # edge / abs(fair_value)
    risk_reward_ratio: float         # max_profit / max_loss
    breakeven_sigmas: float          # breakeven distance in sigma units


def evaluate_opportunity(
    pricing: PricingContext,
    entry_config: dict| None = None,
    risk_config: dict| None = None,
) -> OpportunityEvaluation:
    """
    Evaluate opportunity across 5 dimensions: pricing edge, risk/reward,
    breakeven reachability, execution cost, capital efficiency.

    Args:
        pricing: PricingContext from L3 pricing layer
        entry_config: Config with entry thresholds (optional)
        risk_config: Config with risk limits (optional)

    Returns:
        OpportunityEvaluation with composite_score 0-100
    """
    if entry_config is None:
        entry_config = {}
    if risk_config is None:
        risk_config = {}

    # Extract parameters
    max_bid_ask_pct = risk_config.get("max_bid_ask_pct", 0.15)

    # 1. Pricing Edge Score (35% weight)
    pricing_edge_score = _calculate_pricing_edge_score(pricing)

    # 2. Risk/Reward Score (25% weight)
    risk_reward_score, rr_ratio = _calculate_risk_reward_score(pricing)

    # 3. Breakeven Score (20% weight)
    breakeven_score, breakeven_sigmas = _calculate_breakeven_score(pricing)

    # 4. Execution Cost Score (15% weight)
    execution_cost_score = _calculate_execution_cost_score(pricing, max_bid_ask_pct)

    # 5. Capital Efficiency Score (5% weight)
    capital_efficiency_score, _ = _calculate_capital_efficiency_score(pricing, risk_reward_score)

    # Composite score (weighted average)
    composite_score = (
        pricing_edge_score * 0.35 +
        risk_reward_score * 0.25 +
        breakeven_score * 0.20 +
        execution_cost_score * 0.15 +
        capital_efficiency_score * 0.05
    )

    # Edge percentage for raw values
    edge_pct = _safe_divide(pricing.edge, abs(pricing.fair_value), 0.0)

    return OpportunityEvaluation(
        strategy_name=pricing.strategy_name,
        pricing_edge_score=pricing_edge_score,
        risk_reward_score=risk_reward_score,
        breakeven_score=breakeven_score,
        execution_cost_score=execution_cost_score,
        capital_efficiency_score=capital_efficiency_score,
        composite_score=composite_score,
        edge_pct=edge_pct,
        risk_reward_ratio=rr_ratio,
        breakeven_sigmas=breakeven_sigmas,
    )


def _calculate_pricing_edge_score(pricing: PricingContext) -> float:
    """
    Pricing Edge Score (35%): quanto vale di più la posizione rispetto a quanto la paghiamo.

    Formula: edge / abs(fair_value) * 200
    - edge_pct = 0.50 → score 100
    - edge_pct = 0.00 → score 0
    - edge_pct < 0 → score 0
    """
    if abs(pricing.fair_value) < 0.01:
        return 0.0

    edge_pct = pricing.edge / abs(pricing.fair_value)
    score = max(0.0, min(100.0, edge_pct * 200))
    return float(score)


def _calculate_risk_reward_score(pricing: PricingContext) -> tuple[float, float]:
    """
    Risk/Reward Score (25%): rapporto tra profitto massimo e perdita massima.

    Stima max_profit e max_loss dai strikes e fair_value.
    Formula: (max_profit / max_loss) * 50
    - rr_ratio = 2.0 → score 100
    - rr_ratio = 1.0 → score 50
    - rr_ratio = 0.0 → score 0
    """
    if len(pricing.strikes) < 2:
        return 0.0, 0.0

    strikes_list = list(pricing.strikes.values())
    spread_width = max(strikes_list) - min(strikes_list)

    if spread_width < 0.01:
        return 0.0, 0.0

    # Determine strategy type from fair_value sign
    if pricing.fair_value < 0:  # Credit strategy
        max_profit = abs(pricing.fair_value)
        max_loss = max(0.01, spread_width - abs(pricing.fair_value))
    else:  # Debit strategy
        max_profit = max(0.0, spread_width - pricing.fair_value)
        max_loss = max(0.01, pricing.fair_value)

    if max_loss < 0.01:
        return 0.0, 0.0

    rr_ratio = max_profit / max_loss
    score = min(100.0, rr_ratio * 50)

    return float(score), float(rr_ratio)


def _calculate_breakeven_score(pricing: PricingContext) -> tuple[float, float]:
    """
    Breakeven Score (20%): distanza del breakeven in unità sigma.

    Formula: 100 - breakeven_sigmas * 20
    - breakeven_sigmas < 1 → score alto (breakeven vicino)
    - breakeven_sigmas > 5 → score 0
    """
    if pricing.dte_days <= 0 or pricing.iv <= 0.001 or pricing.spot <= 0:
        return 0.0, 99.0

    # Expected move (1 sigma)
    expected_move = pricing.spot * pricing.iv * np.sqrt(pricing.dte_days / 365.0)

    if expected_move < 0.001:
        return 0.0, 99.0

    breakeven_sigmas = abs(pricing.breakeven_distance) / expected_move
    score = max(0.0, 100.0 - breakeven_sigmas * 20)

    return float(score), float(breakeven_sigmas)


def _calculate_execution_cost_score(pricing: PricingContext, max_bid_ask_pct: float = 0.15) -> float:
    """
    Execution Cost Score (15%): quanto pesa il bid/ask spread.

    Formula: (1 - bid_ask_pct / max_bid_ask_pct) * 100
    - bid_ask_pct = 0.00 → score 100
    - bid_ask_pct = max_bid_ask_pct → score 0
    """
    if max_bid_ask_pct < 0.001:
        max_bid_ask_pct = 0.15

    score = max(0.0, min(100.0, (1 - pricing.bid_ask_pct / max_bid_ask_pct) * 100))
    return float(score)


def _calculate_capital_efficiency_score(pricing: PricingContext, risk_reward_score: float) -> tuple[float, float]:
    """
    Capital Efficiency Score (5%): efficienza del theta per unità di rischio.

    Formula: (theta_daily / max_loss * 365) * 500
    - theta efficiency = 20% annuale → score 100
    """
    # Use risk_reward_score to estimate max_loss indirectly
    # If we don't have direct max_loss, use fair_value as proxy
    if abs(pricing.fair_value) < 0.01:
        return 0.0, 0.0

    theta_daily = abs(pricing.theta)
    max_loss = abs(pricing.fair_value)

    if max_loss < 0.01:
        return 0.0, 0.0

    theta_efficiency = theta_daily / max_loss * 365.0
    score = min(100.0, theta_efficiency * 500)

    return float(score), float(theta_efficiency)


def _safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division with default value for division by zero."""
    if abs(denominator) < 0.001:
        return default
    return numerator / denominator
