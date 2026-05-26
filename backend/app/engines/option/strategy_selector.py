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


STRATEGY_BY_NAME: dict = {
    "bull_put_spread":           bull_put_strategy,
    "bear_call_spread":          bear_call_strategy,
    "put_broken_wing_butterfly": neutral_broken_wing_strategy,
    "bull_call_spread":          bull_call_spread_strategy,
    "bear_put_spread":           bear_put_spread_strategy,
    "long_straddle":             long_straddle_strategy,
    "long_strangle":             long_strangle_strategy,
    "iron_condor":               iron_condor_strategy,
    "iron_butterfly":            iron_butterfly_strategy,
    "calendar_spread":           calendar_spread_strategy,
    "jade_lizard":               jade_lizard_strategy,
    "reverse_jade_lizard":       reverse_jade_lizard_strategy,
    "diagonal_spread":           diagonal_spread_strategy,
}

STRATEGY_MATRIX = {
    Zone.A: {
        Trend.UP:      [bull_call_spread_strategy],
        Trend.DOWN:    [bear_put_spread_strategy],
        Trend.NEUTRAL: [neutral_broken_wing_strategy],
    },
    Zone.B: {
        Trend.UP:      [bull_put_strategy, jade_lizard_strategy],
        Trend.DOWN:    [bear_call_strategy, reverse_jade_lizard_strategy],
        Trend.NEUTRAL: [no_trade_strategy],
    },
    Zone.C: {
        "high_squeeze":   [long_straddle_strategy],
        "medium_squeeze": [long_strangle_strategy],
        "low_squeeze":    [neutral_broken_wing_strategy],
    },
    Zone.D: {
        "very_high_iv": [iron_butterfly_strategy],
        "high_iv":      [iron_condor_strategy, calendar_spread_strategy],
        "neutral":      [jade_lizard_strategy, diagonal_spread_strategy],
    },
}

# IV rank threshold above which more aggressive premium-selling is warranted (Zone B)
_IV_RANK_AGGRESSIVE = 50.0
# ADX threshold below which the market is considered ultra-lateral (Zone D / Calendar)
_ADX_ULTRA_LATERAL = 15.0


def select_strategy(
    zone: Zone,
    trend,
    squeeze_intensity: float = 0,
    iv_rank: float = 50,
    adx: float = 20,
    trend_signal: int = 0,
    entry_score: float = 50,
    strategy_overrides: dict | None = None,
) -> StrategySpec:
    """
    Select strategy based on zone and market conditions.

    See ADR 005 for the full zone × strategy matrix and ranking criteria.

    Args:
        zone: Zone A/B/C/D from zone_classifier
        trend: Trend enum (UP/DOWN/NEUTRAL) for Zone A/B
        squeeze_intensity: 0-100 for Zone C sub-classification
        iv_rank: 0-100, used for Zone B/D ranking
        adx: 0-100, used for Zone D Calendar vs IC ranking
        trend_signal: raw int signal (-1/0/1), used for Zone D Diagonal ranking
        entry_score: 0-100, converted to size_multiplier
        strategy_overrides: per-strategy config dict from strategy_config.overrides parameter

    Returns:
        StrategySpec with size_multiplier applied, or no_trade if strategy is disabled
    """
    overrides = strategy_overrides or {}
    zone_str = zone.value  # "A", "B", "C", "D"
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

    # Filter out disabled strategies before ranking (zone-specific enabled flag)
    enabled_candidates = [
        c for c in candidates
        if overrides.get(c().name, {}).get(zone_str, {}).get("enabled", True)
    ]
    if not enabled_candidates:
        return no_trade_strategy()

    if len(enabled_candidates) == 1:
        spec = enabled_candidates[0]()
    else:
        spec = rank_strategies(enabled_candidates, zone, iv_rank, adx, trend_signal)

    base_size = calculate_position_size(entry_score)
    strategy_cfg = overrides.get(spec.name, {}).get(zone_str, {})
    spec.size_multiplier = base_size * strategy_cfg.get("size_multiplier", 1.0)
    return spec


def rank_strategies(
    candidates: list,
    zone: Zone,
    iv_rank: float,
    adx: float,
    trend_signal: int,
) -> StrategySpec:
    """
    Rank candidates by market conditions — see ADR 005.

    Zone B UP:   BPS vs Jade Lizard       → JL when iv_rank > 50 (more premium available)
    Zone B DOWN: BCS vs Reverse JL        → RJL when iv_rank > 50
    Zone D high_iv: IC vs Calendar        → Calendar when adx < 15 (ultra-lateral)
    Zone D neutral: JL vs Diagonal        → Diagonal when abs(trend_signal) > 0
    """
    if len(candidates) == 1:
        return candidates[0]()

    if zone == Zone.B:
        # candidates[0] = BPS or BCS (conservative), candidates[1] = JL or RJL (aggressive)
        if iv_rank > _IV_RANK_AGGRESSIVE:
            return candidates[1]()
        return candidates[0]()

    if zone == Zone.D:
        # high_iv: candidates[0]=IC, candidates[1]=Calendar
        # neutral:  candidates[0]=JL, candidates[1]=Diagonal
        if adx < _ADX_ULTRA_LATERAL or abs(trend_signal) > 0:
            return candidates[1]()
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
