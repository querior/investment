from .strategy_builder import create_iron_butterfly
from .base import StrategySpec


def iron_butterfly_strategy() -> StrategySpec:
    return StrategySpec(
        name="iron_butterfly",
        builder=create_iron_butterfly,
        should_trade=True,
    )
