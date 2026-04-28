from .models import Zone


def classify_zone(iv_rank: float, adx: float) -> Zone:
    """Classify market regime into one of 4 zones.

    Uses a 2x2 matrix based on IV regime (volatility level) and
    trend direction (ADX strength).

    Args:
        iv_rank: IV percentile (0-100). Below 30 = low IV, 30+ = high IV
        adx: Average Directional Index (0-100). 25+ = directional, below 25 = lateral

    Returns:
        Zone: One of A, B, C, D, or UNKNOWN

    Matrix:
        ┌────────────────┬─────────────┬─────────────┐
        │                │ IV Low <30  │ IV High ≥30 │
        ├────────────────┼─────────────┼─────────────┤
        │ ADX >25 (Trend)│ Zone A      │ Zone B      │
        │ ADX ≤25(Lateral│ Zone C      │ Zone D      │
        └────────────────┴─────────────┴─────────────┘

    Zone Characteristics:
        A (Trend + Low IV): Breakout setup, use debit spreads (Bull Call, Bear Put)
        B (Trend + High IV): Credit spreads, sell premium (Bull Put, Bear Call)
        C (Lateral + Low IV): Squeeze reversal, long volatility (Straddle, Strangle)
        D (Lateral + High IV): Vol crush, iron structures (Iron Condor, Butterfly)
    """
    iv_threshold = 30
    adx_threshold = 25

    is_directional = adx >= adx_threshold
    is_iv_low = iv_rank < iv_threshold

    if is_directional and is_iv_low:
        return Zone.A
    elif is_directional and not is_iv_low:
        return Zone.B
    elif not is_directional and is_iv_low:
        return Zone.C
    elif not is_directional and not is_iv_low:
        return Zone.D
    else:
        return Zone.UNKNOWN
