from .strategy_builder import create_bull_put_spread
from .base import StrategySpec

def bull_put_strategy() -> StrategySpec:
    return StrategySpec(
        name="bull_put_spread",
        builder=create_bull_put_spread,
        should_trade=True,
    )
