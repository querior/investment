from .strategy_builder import create_long_straddle
from .base import StrategySpec


def long_straddle_strategy() -> StrategySpec:
    return StrategySpec(
        name="long_straddle",
        builder=create_long_straddle,
        should_trade=True,
    )
