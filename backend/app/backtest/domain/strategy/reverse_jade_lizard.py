from .strategy_builder import create_reverse_jade_lizard
from .base import StrategySpec


def reverse_jade_lizard_strategy() -> StrategySpec:
    return StrategySpec(
        name="reverse_jade_lizard",
        builder=create_reverse_jade_lizard,
        should_trade=True,
    )
