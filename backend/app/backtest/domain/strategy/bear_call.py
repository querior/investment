from .strategy_builder import create_bear_call_spread
from .base import StrategySpec

def bear_call_strategy() -> StrategySpec:
    return StrategySpec(
        name="bear_call_spread",
        builder=create_bear_call_spread,
        should_trade=True,
    )
