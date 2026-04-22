from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import pandas as pd
from app.backtest.domain.models import Position


@dataclass
class ExitContext:
    position: Position
    row: pd.Series
    snapshot: Optional[object] = field(default=None)    # BacktestPositionSnapshot — greche
    entry_row: Optional[pd.Series] = field(default=None) # contesto al momento dell'apertura
    exit_config: dict = field(default_factory=dict)      # parametri regole configurati per run
