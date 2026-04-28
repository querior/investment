from .strategy_builder import create_bear_put_spread
from .base import StrategySpec


def bear_put_spread_strategy() -> StrategySpec:
    return StrategySpec(
        name="bear_put_spread",
        builder=create_bear_put_spread,
        should_trade=True,
    )
