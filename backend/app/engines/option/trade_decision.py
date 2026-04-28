from enum import Enum
from dataclasses import dataclass
from .opportunity_evaluator import OpportunityEvaluation


class TradeAction(Enum):
    """Trade decision action."""
    OPEN = "OPEN"           # Score > threshold_open — high confidence, execute
    MONITOR = "MONITOR"     # threshold_skip ≤ Score ≤ threshold_open — moderate, watch
    SKIP = "SKIP"           # Score < threshold_skip — low confidence, skip


@dataclass
class TradeDecision:
    """Final trade decision after L1→L4 pipeline."""

    action: TradeAction
    score: float             # OpportunityEvaluation.composite_score
    reasoning: str           # Brief explanation of decision
    threshold_open: float    # Threshold for OPEN (default 75)
    threshold_skip: float    # Threshold for SKIP (default 60)


def make_trade_decision(
    evaluation: OpportunityEvaluation,
    position_config: dict | None = None,
) -> TradeDecision:
    """
    L5: Final trade decision gate based on opportunity evaluation score.

    Decision Logic:
    - score > threshold_open → OPEN (execute trade)
    - threshold_skip ≤ score ≤ threshold_open → MONITOR (track but don't open)
    - score < threshold_skip → SKIP (reject)

    Args:
        evaluation: OpportunityEvaluation from L4
        position_config: Config with decision thresholds (optional)

    Returns:
        TradeDecision with action (OPEN/MONITOR/SKIP) + reasoning
    """
    if position_config is None:
        position_config = {}

    # Extract thresholds
    threshold_open = position_config.get("decision_threshold_open", 75.0)
    threshold_skip = position_config.get("decision_threshold_skip", 60.0)

    # Ensure thresholds are valid
    if threshold_open <= threshold_skip:
        threshold_open = 75.0
        threshold_skip = 60.0

    score = evaluation.composite_score

    # Determine action based on score
    if score > threshold_open:
        action = TradeAction.OPEN
        reasoning = f"High confidence ({score:.0f} > {threshold_open}): strong edge + R/R + low execution cost"
    elif score >= threshold_skip:
        action = TradeAction.MONITOR
        reasoning = f"Moderate confidence ({threshold_skip} ≤ {score:.0f} ≤ {threshold_open}): worth tracking"
    else:
        action = TradeAction.SKIP
        reasoning = f"Low confidence ({score:.0f} < {threshold_skip}): insufficient edge or high execution cost"

    return TradeDecision(
        action=action,
        score=score,
        reasoning=reasoning,
        threshold_open=threshold_open,
        threshold_skip=threshold_skip,
    )
