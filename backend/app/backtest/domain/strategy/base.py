from dataclasses import dataclass
from typing import Callable
from app.backtest.domain.models import Position

@dataclass
class StrategySpec:
    name: str
    builder: Callable[..., Position]
    should_trade: bool = True
    size_multiplier: float = 1.0  # Position size multiplier (0.0-1.0) based on entry score