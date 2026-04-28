import pytest
from app.engines.option.models import Zone
from app.engines.option.zone_classifier import classify_zone


class TestZoneClassification:
    """Unit tests for zone classification logic."""

    def test_zone_a_directional_low_iv(self):
        """Zone A: Directional trend + Low IV (breakout setup)."""
        assert classify_zone(iv_rank=20, adx=30) == Zone.A
        assert classify_zone(iv_rank=10, adx=50) == Zone.A
        assert classify_zone(iv_rank=29, adx=26) == Zone.A

    def test_zone_b_directional_high_iv(self):
        """Zone B: Directional trend + High IV (credit spreads)."""
        assert classify_zone(iv_rank=70, adx=35) == Zone.B
        assert classify_zone(iv_rank=90, adx=40) == Zone.B
        assert classify_zone(iv_rank=31, adx=50) == Zone.B

    def test_zone_c_lateral_low_iv(self):
        """Zone C: Lateral movement + Low IV (squeeze reversal)."""
        assert classify_zone(iv_rank=15, adx=20) == Zone.C
        assert classify_zone(iv_rank=5, adx=10) == Zone.C
        assert classify_zone(iv_rank=29, adx=15) == Zone.C

    def test_zone_d_lateral_high_iv(self):
        """Zone D: Lateral movement + High IV (vol crush setup)."""
        assert classify_zone(iv_rank=75, adx=18) == Zone.D
        assert classify_zone(iv_rank=80, adx=20) == Zone.D
        assert classify_zone(iv_rank=50, adx=24) == Zone.D

    def test_boundary_iv_threshold(self):
        """Test IV boundary at 30."""
        # Just below threshold (low IV)
        assert classify_zone(iv_rank=29.9, adx=30) == Zone.A
        # At threshold (high IV)
        assert classify_zone(iv_rank=30.0, adx=30) == Zone.B
        # Just above threshold (high IV)
        assert classify_zone(iv_rank=30.1, adx=30) == Zone.B

    def test_boundary_adx_threshold(self):
        """Test ADX boundary at 25 (inclusive - 25+ is directional)."""
        # Just below threshold (lateral)
        assert classify_zone(iv_rank=20, adx=24.9) == Zone.C
        # At threshold (directional - inclusive)
        assert classify_zone(iv_rank=20, adx=25.0) == Zone.A
        # Just above threshold (directional)
        assert classify_zone(iv_rank=20, adx=25.1) == Zone.A

    def test_extreme_values(self):
        """Test extreme IV and ADX values."""
        assert classify_zone(iv_rank=0, adx=100) == Zone.A
        assert classify_zone(iv_rank=100, adx=0) == Zone.D
        assert classify_zone(iv_rank=100, adx=100) == Zone.B
        assert classify_zone(iv_rank=0, adx=0) == Zone.C

    def test_realistic_market_scenarios(self):
        """Test realistic market conditions."""
        # Strong uptrend, low volatility (breakout in progress)
        assert classify_zone(iv_rank=15, adx=45) == Zone.A

        # Strong rally, elevated IV (correction or market excitement)
        assert classify_zone(iv_rank=65, adx=40) == Zone.B

        # Range-bound, tight volatility (compression phase)
        assert classify_zone(iv_rank=20, adx=15) == Zone.C

        # Range-bound, high volatility (waiting for breakout)
        assert classify_zone(iv_rank=80, adx=18) == Zone.D
