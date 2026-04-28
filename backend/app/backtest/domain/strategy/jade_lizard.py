from .strategy_builder import create_jade_lizard
from .base import StrategySpec


def jade_lizard_strategy() -> StrategySpec:
    return StrategySpec(
        name="jade_lizard",
        builder=create_jade_lizard,
        should_trade=True,
    )
