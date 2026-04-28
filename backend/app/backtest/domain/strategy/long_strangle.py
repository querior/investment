from .strategy_builder import create_long_strangle
from .base import StrategySpec


def long_strangle_strategy() -> StrategySpec:
    return StrategySpec(
        name="long_strangle",
        builder=create_long_strangle,
        should_trade=True,
    )
