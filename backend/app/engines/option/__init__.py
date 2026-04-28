"""Option Decision Engine — L1→L5 decision pipeline."""

from .models import Zone, Trend
from .zone_classifier import classify_zone
from .strategy_selector import select_strategy, calculate_position_size
from .pricing import PricingContext, calculate_pricing
from .greeks_calculator import calculate_delta, calculate_gamma, calculate_vega, calculate_theta
from .opportunity_evaluator import OpportunityEvaluation, evaluate_opportunity
from .trade_decision import TradeAction, TradeDecision, make_trade_decision
from .engine import DecisionEngine

__all__ = [
    # Core enums & dataclasses
    "Zone",
    "Trend",
    "PricingContext",
    "OpportunityEvaluation",
    "TradeAction",
    "TradeDecision",
    # Functions
    "classify_zone",
    "select_strategy",
    "calculate_position_size",
    "calculate_pricing",
    "calculate_delta",
    "calculate_gamma",
    "calculate_vega",
    "calculate_theta",
    "evaluate_opportunity",
    "make_trade_decision",
    # Engine
    "DecisionEngine",
]
