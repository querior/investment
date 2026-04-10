from .base import StrategySpec

def no_trade_strategy() -> StrategySpec:
    return StrategySpec(
        name="no_trade",
        builder=None, # type: ignore
        should_trade=False,
    )