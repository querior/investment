from .strategy_builder import create_bull_call_spread
from .base import StrategySpec


def bull_call_spread_strategy() -> StrategySpec:
    return StrategySpec(
        name="bull_call_spread",
        builder=create_bull_call_spread,
        should_trade=True,
    )
