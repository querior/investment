from app.backtest.domain.strategy.bull_put import bull_put_strategy
from app.backtest.domain.strategy.bear_call import bear_call_strategy
from app.backtest.domain.strategy.neutral_broken_wing import neutral_broken_wing_strategy
from app.backtest.domain.strategy.bull_call import bull_call_spread_strategy
from app.backtest.domain.strategy.bear_put import bear_put_spread_strategy
from app.backtest.domain.strategy.long_straddle import long_straddle_strategy
from app.backtest.domain.strategy.long_strangle import long_strangle_strategy
from app.backtest.domain.strategy.iron_condor import iron_condor_strategy
from app.backtest.domain.strategy.iron_butterfly import iron_butterfly_strategy
from app.backtest.domain.strategy.calendar_spread import calendar_spread_strategy
from app.backtest.domain.strategy.jade_lizard import jade_lizard_strategy
from app.backtest.domain.strategy.reverse_jade_lizard import reverse_jade_lizard_strategy
from app.backtest.domain.strategy.diagonal_spread import diagonal_spread_strategy
from app.backtest.domain.strategy.no_trade import no_trade_strategy

from app.backtest.domain.strategy.base import StrategySpec
from .models import Zone, Trend


STRATEGY_MATRIX = {
    Zone.A: {
        Trend.UP: [bull_call_spread_strategy],
        Trend.DOWN: [bear_put_spread_strategy],
        Trend.NEUTRAL: [neutral_broken_wing_strategy],
    },
    Zone.B: {
        Trend.UP: [bull_put_strategy, jade_lizard_strategy],
        Trend.DOWN: [bear_call_strategy, reverse_jade_lizard_strategy],
        Trend.NEUTRAL: [no_trade_strategy],
    },
    Zone.C: {
        "high_squeeze": [long_straddle_strategy],
        "medium_squeeze": [long_strangle_strategy],
        "low_squeeze": [neutral_broken_wing_strategy],
    },
    Zone.D: {
        "very_high_iv": [iron_butterfly_strategy],
        "high_iv": [iron_condor_strategy, calendar_spread_strategy],
        "neutral": [jade_lizard_strategy, diagonal_spread_strategy],
    },
}


def select_strategy(
    zone: Zone,
    trend,
    squeeze_intensity: float = 0,
    iv_rank: float = 50,
    entry_score: float = 50,
) -> StrategySpec:
    """
    Select strategy based on zone and conditions.

    Args:
        zone: Zone A/B/C/D from zone_classifier
        trend: Trend.UP/DOWN/NEUTRAL or string condition for Zone C/D
        squeeze_intensity: 0-100 for Zone C sub-classification
        iv_rank: 0-100 for Zone D sub-classification
        entry_score: 0-100, converted to size_multiplier

    Returns:
        StrategySpec with size_multiplier applied
    """
    condition = trend

    if zone == Zone.C:
        if squeeze_intensity > 70:
            condition = "high_squeeze"
        elif squeeze_intensity > 50:
            condition = "medium_squeeze"
        else:
            condition = "low_squeeze"
    elif zone == Zone.D:
        if iv_rank > 65:
            condition = "very_high_iv"
        elif iv_rank > 50:
            condition = "high_iv"
        else:
            condition = "neutral"

    try:
        candidates = STRATEGY_MATRIX[zone][condition]
    except KeyError:
        return no_trade_strategy()

    if not candidates:
        return no_trade_strategy()

    if len(candidates) == 1:
        spec = candidates[0]()
        spec.size_multiplier = calculate_position_size(entry_score)
        return spec

    best = rank_strategies(candidates, entry_score, iv_rank, zone)
    best.size_multiplier = calculate_position_size(entry_score)
    return best


def rank_strategies(
    candidates: list,
    entry_score: float,
    iv_rank: float,
    zone: Zone,
) -> StrategySpec:
    """Rank strategies by quality metrics when multiple candidates exist."""
    if len(candidates) == 1:
        return candidates[0]()

    if zone == Zone.B:
        return candidates[0]()

    if zone == Zone.D:
        return candidates[0]()

    return candidates[0]()


def calculate_position_size(entry_score: float) -> float:
    """Convert entry_score (0-100) to size_multiplier (0.0-1.0)."""
    threshold_full = 75
    threshold_reduced = 60
    multiplier_full = 1.0
    multiplier_reduced = 0.75

    if entry_score >= threshold_full:
        return multiplier_full
    elif entry_score >= threshold_reduced:
        progress = (entry_score - threshold_reduced) / (threshold_full - threshold_reduced)
        return multiplier_reduced + progress * (multiplier_full - multiplier_reduced)
    else:
        return 0.0
