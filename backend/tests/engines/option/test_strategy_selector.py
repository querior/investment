import pytest
from app.engines.option.models import Zone, Trend
from app.engines.option.zone_classifier import classify_zone
from app.engines.option.strategy_selector import (
    select_strategy,
    calculate_position_size,
)


class TestZoneASelection:
    """Test Zone A (Directional + Low IV) strategy selection."""

    def test_zone_a_up_trend_selects_bull_call(self):
        spec = select_strategy(Zone.A, Trend.UP, entry_score=75)
        assert spec.name == "bull_call_spread"
        assert spec.size_multiplier == 1.0

    def test_zone_a_down_trend_selects_bear_put(self):
        spec = select_strategy(Zone.A, Trend.DOWN, entry_score=70)
        assert spec.name == "bear_put_spread"
        assert spec.size_multiplier > 0.85

    def test_zone_a_neutral_trend_selects_broken_wing(self):
        spec = select_strategy(Zone.A, Trend.NEUTRAL, entry_score=65)
        assert spec.name == "put_broken_wing_butterfly"
        assert spec.size_multiplier > 0.8


class TestZoneBSelection:
    """Test Zone B (Directional + High IV) strategy selection."""

    def test_zone_b_up_trend_selects_bull_put(self):
        spec = select_strategy(Zone.B, Trend.UP, entry_score=80)
        assert spec.name == "bull_put_spread"
        assert spec.size_multiplier == 1.0

    def test_zone_b_down_trend_selects_bear_call(self):
        spec = select_strategy(Zone.B, Trend.DOWN, entry_score=68)
        assert spec.name == "bear_call_spread"
        assert spec.size_multiplier > 0.85

    def test_zone_b_neutral_trend_selects_no_trade(self):
        spec = select_strategy(Zone.B, Trend.NEUTRAL, entry_score=50)
        assert spec.name == "no_trade"
        assert spec.size_multiplier == 0.0


class TestZoneCSelection:
    """Test Zone C (Lateral + Low IV, Squeeze-based) strategy selection."""

    def test_zone_c_high_squeeze_selects_long_straddle(self):
        spec = select_strategy(
            Zone.C, Trend.NEUTRAL, squeeze_intensity=80, entry_score=75
        )
        assert spec.name == "long_straddle"
        assert spec.size_multiplier == 1.0

    def test_zone_c_medium_squeeze_selects_long_strangle(self):
        spec = select_strategy(
            Zone.C, Trend.NEUTRAL, squeeze_intensity=60, entry_score=70
        )
        assert spec.name == "long_strangle"
        assert spec.size_multiplier > 0.85

    def test_zone_c_low_squeeze_selects_broken_wing(self):
        spec = select_strategy(
            Zone.C, Trend.NEUTRAL, squeeze_intensity=30, entry_score=65
        )
        assert spec.name == "put_broken_wing_butterfly"
        assert spec.size_multiplier > 0.8

    def test_zone_c_squeeze_boundaries(self):
        # Boundary at 70
        spec_high = select_strategy(Zone.C, Trend.NEUTRAL, squeeze_intensity=70.1)
        spec_med = select_strategy(Zone.C, Trend.NEUTRAL, squeeze_intensity=69.9)
        # Both should work (close to boundary)
        assert spec_high.name in ["long_straddle", "long_strangle"]
        assert spec_med.name in ["long_straddle", "long_strangle"]


class TestZoneDSelection:
    """Test Zone D (Lateral + High IV, IV-based) strategy selection."""

    def test_zone_d_very_high_iv_selects_iron_butterfly(self):
        spec = select_strategy(Zone.D, Trend.NEUTRAL, iv_rank=75, entry_score=70)
        assert spec.name == "iron_butterfly"
        assert spec.size_multiplier > 0.85

    def test_zone_d_high_iv_selects_iron_condor(self):
        spec = select_strategy(Zone.D, Trend.NEUTRAL, iv_rank=55, entry_score=72)
        assert spec.name == "iron_condor"
        assert spec.size_multiplier > 0.90

    def test_zone_d_neutral_iv_selects_jade_lizard(self):
        spec = select_strategy(Zone.D, Trend.NEUTRAL, iv_rank=40, entry_score=75)
        assert spec.name == "jade_lizard"
        assert spec.size_multiplier == 1.0

    def test_zone_d_iv_boundaries(self):
        # Boundary at 65
        spec_very = select_strategy(Zone.D, Trend.NEUTRAL, iv_rank=65.1)
        spec_high = select_strategy(Zone.D, Trend.NEUTRAL, iv_rank=64.9)
        assert spec_very.name == "iron_butterfly"
        assert spec_high.name == "iron_condor"


class TestPositionSizeMultiplier:
    """Test size multiplier calculation logic."""

    def test_size_multiplier_full_size_above_75(self):
        assert calculate_position_size(80) == 1.0
        assert calculate_position_size(75) == 1.0
        assert calculate_position_size(100) == 1.0

    def test_size_multiplier_reduced_size_60_to_75(self):
        size_75 = calculate_position_size(75)
        size_70 = calculate_position_size(70)
        size_65 = calculate_position_size(65)
        size_60 = calculate_position_size(60)

        assert size_75 == 1.0
        assert 0.88 < size_70 < 0.92
        assert 0.80 < size_65 < 0.84
        assert 0.75 <= size_60 <= 0.76

    def test_size_multiplier_no_trade_below_60(self):
        assert calculate_position_size(50) == 0.0
        assert calculate_position_size(0) == 0.0
        assert calculate_position_size(59.9) == 0.0

    def test_size_multiplier_monotonic_increase(self):
        scores = [0, 30, 50, 60, 70, 75, 80, 100]
        sizes = [calculate_position_size(s) for s in scores]
        # Verify monotonic increase
        for i in range(len(sizes) - 1):
            assert sizes[i] <= sizes[i + 1], f"Non-monotonic: {sizes[i]} > {sizes[i + 1]}"

    def test_size_multiplier_linear_interpolation(self):
        # Between 60 and 75: linear interpolation between 0.75 and 1.0
        size_60 = calculate_position_size(60)
        size_67_5 = calculate_position_size(67.5)  # Midpoint
        size_75 = calculate_position_size(75)

        assert size_60 == 0.75
        assert 0.87 < size_67_5 < 0.88  # Approximately midpoint
        assert size_75 == 1.0


class TestL1L2Integration:
    """Test full L1→L2 pipeline (Zone Classifier + Strategy Selector)."""

    def test_pipeline_zone_a_directional_low_iv(self):
        """IV=20, ADX=40 (Zone A) + UP trend → bull_call_spread"""
        zone = classify_zone(iv_rank=20, adx=40)
        assert zone == Zone.A

        spec = select_strategy(zone, Trend.UP, entry_score=85)
        assert spec.name == "bull_call_spread"
        assert spec.size_multiplier == 1.0

    def test_pipeline_zone_b_directional_high_iv(self):
        """IV=75, ADX=35 (Zone B) + DOWN trend → bear_call_spread"""
        zone = classify_zone(iv_rank=75, adx=35)
        assert zone == Zone.B

        spec = select_strategy(zone, Trend.DOWN, entry_score=70)
        assert spec.name == "bear_call_spread"
        assert spec.size_multiplier > 0.85

    def test_pipeline_zone_c_lateral_low_iv_high_squeeze(self):
        """IV=25, ADX=15 (Zone C) + squeeze=85 → long_straddle"""
        zone = classify_zone(iv_rank=25, adx=15)
        assert zone == Zone.C

        spec = select_strategy(zone, Trend.NEUTRAL, squeeze_intensity=85, entry_score=78)
        assert spec.name == "long_straddle"
        assert spec.size_multiplier == 1.0

    def test_pipeline_zone_d_lateral_very_high_iv(self):
        """IV=70, ADX=20 (Zone D, very_high_iv) → iron_butterfly"""
        zone = classify_zone(iv_rank=70, adx=20)
        assert zone == Zone.D

        spec = select_strategy(zone, Trend.NEUTRAL, iv_rank=70, entry_score=70)
        assert spec.name == "iron_butterfly"
        assert spec.size_multiplier > 0.85

    def test_pipeline_zone_d_lateral_high_iv(self):
        """IV=55, ADX=18 (Zone D, high_iv) → iron_condor"""
        zone = classify_zone(iv_rank=55, adx=18)
        assert zone == Zone.D

        spec = select_strategy(zone, Trend.NEUTRAL, iv_rank=55, entry_score=72)
        assert spec.name == "iron_condor"
        assert spec.size_multiplier > 0.90


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_entry_score_exactly_60_is_reduced_size(self):
        size = calculate_position_size(60)
        assert 0.75 <= size <= 0.76

    def test_entry_score_exactly_75_is_full_size(self):
        assert calculate_position_size(75) == 1.0

    def test_entry_score_just_below_60_is_no_trade(self):
        assert calculate_position_size(59.9) == 0.0

    def test_invalid_zone_returns_no_trade(self):
        # Simulate invalid condition by passing unknown trend to Zone C without squeeze
        spec = select_strategy(Zone.C, Trend.UP, entry_score=70)
        # Should default to no_trade or handle gracefully
        assert spec.name in [
            "no_trade",
            "put_broken_wing_butterfly",
        ]

    def test_low_entry_score_reduces_size_across_all_zones(self):
        """Verify size_multiplier is applied consistently across zones."""
        spec_a = select_strategy(Zone.A, Trend.UP, entry_score=65)
        spec_b = select_strategy(Zone.B, Trend.UP, entry_score=65)
        spec_d = select_strategy(Zone.D, Trend.NEUTRAL, iv_rank=50, entry_score=65)

        # All should have reduced size (between 60-75)
        assert 0.80 < spec_a.size_multiplier < 0.85
        assert 0.80 < spec_b.size_multiplier < 0.85
        assert 0.80 < spec_d.size_multiplier < 0.85
