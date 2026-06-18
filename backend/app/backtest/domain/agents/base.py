from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class LayerContext:
    """Identity tag for every component — enables GlobalOrchestrator coordination (future)."""
    layer: Literal["short", "medium", "long"]
    market: str       # "options", "equities", "futures"
    instrument: str   # "SPY", "QQQ", ...
    timeframe: str    # "daily", "weekly", "monthly"


@dataclass
class ExitSignal:
    """Decision produced by ExitAgent for a single open position."""
    action: Literal["HOLD", "CLOSE", "ROLL"]
    reason: str
    triggered_by: str = ""
    exit_conditions: dict | None = field(default=None)
