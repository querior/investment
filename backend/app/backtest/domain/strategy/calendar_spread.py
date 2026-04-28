from .strategy_builder import create_calendar_spread
from .base import StrategySpec


def calendar_spread_strategy() -> StrategySpec:
    return StrategySpec(
        name="calendar_spread",
        builder=create_calendar_spread,
        should_trade=True,
    )
