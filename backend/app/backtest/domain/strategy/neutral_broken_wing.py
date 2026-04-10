from .base import StrategySpec
from app.backtest.domain.strategy.strategy_builder import create_put_broken_wing_butterfly

def neutral_broken_wing_strategy() -> StrategySpec:
    return StrategySpec(
        name="put_broken_wing_butterfly",
        builder=create_put_broken_wing_butterfly,
        should_trade=True,
    )