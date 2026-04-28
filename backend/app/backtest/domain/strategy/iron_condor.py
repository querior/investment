from .strategy_builder import create_iron_condor
from .base import StrategySpec


def iron_condor_strategy() -> StrategySpec:
    return StrategySpec(
        name="iron_condor",
        builder=create_iron_condor,
        should_trade=True,
    )
