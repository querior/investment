from enum import Enum


class Zone(Enum):
    """Market regime classification based on IV and Trend.

    Zone A: Directional + Low IV (breakout setup - long vol with bias)
    Zone B: Directional + High IV (credit spreads)
    Zone C: Lateral + Low IV (long vol - squeeze reversal)
    Zone D: Lateral + High IV (iron condor - vol crush setup)
    """
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    UNKNOWN = "UNKNOWN"


class Trend(Enum):
    """Trend direction derived from technical indicators."""
    UP = 1
    DOWN = -1
    NEUTRAL = 0
