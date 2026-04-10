from dataclasses import dataclass
from typing import Callable
from app.backtest.domain.models import Position

@dataclass
class StrategySpec:
    name: str
    builder: Callable[..., Position]
    should_trade: bool = True