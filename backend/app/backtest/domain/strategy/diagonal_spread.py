from .strategy_builder import create_diagonal_spread
from .base import StrategySpec


def diagonal_spread_strategy() -> StrategySpec:
    return StrategySpec(
        name="diagonal_spread",
        builder=create_diagonal_spread,
        should_trade=True,
    )
