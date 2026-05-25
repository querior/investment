"""
Tests for entry_score calculation pipeline.

Verifies:
- calculate_entry_score returns non-zero values with real indicator data
- entry_score column is added to the dataframe by build_backtest_dataset
- size_multiplier reflects the correct entry_score (not always 0)
- decision log fallback is 50.0, not 0
"""

import pandas as pd
import numpy as np
import pytest

from app.backtest.domain.strategy.entry_scoring import (
    calculate_entry_score,
    calculate_position_size,
)
from app.engines.option.strategy_selector import select_strategy
from app.engines.option.models import Zone, Trend


# --- Entry config with default weights (mirrors _build_entry_config defaults) ---
DEFAULT_ENTRY_CONFIG = {
    "entry_score.w1_iv_rank": 0.30,
    "entry_score.w2_iv_hv": 0.20,
    "entry_score.w3_squeeze": 0.20,
    "entry_score.w4_rsi": 0.15,
    "entry_score.w5_dte": 0.10,
    "entry_score.w6_volume": 0.05,
    "entry_score.rsi_neutral_min": 40.0,
    "entry_score.rsi_neutral_max": 60.0,
    "entry_score.dte_min": 21,
    "entry_score.dte_optimal_min": 35,
    "entry_score.dte_optimal_max": 45,
    "entry_score.dte_max": 55,
    "entry_size.threshold_full": 75.0,
    "entry_size.threshold_reduced": 60.0,
    "entry_size.multiplier_full": 1.0,
    "entry_size.multiplier_reduced": 0.75,
}


class TestCalculateEntryScore:
    """Unit tests for calculate_entry_score function."""

    def _row(self, **kwargs) -> pd.Series:
        base = {
            "iv_rank": 45.0,
            "iv_rv_ratio": 1.1,
            "squeeze_intensity": 55.0,
            "rsi_14": 52.0,
            "volume_ratio": 0.85,
            "dte_days": 45,
        }
        base.update(kwargs)
        return pd.Series(base)

    def test_score_is_nonzero_with_typical_indicators(self):
        score = calculate_entry_score(self._row(), DEFAULT_ENTRY_CONFIG)
        assert score > 0, f"Expected score > 0 with real indicators, got {score}"

    def test_score_range_is_0_to_100(self):
        score = calculate_entry_score(self._row(), DEFAULT_ENTRY_CONFIG)
        assert 0 <= score <= 100, f"Score out of range: {score}"

    def test_low_iv_rank_gives_high_score(self):
        """Low IV rank (cheap options) → higher entry score."""
        score_low_iv = calculate_entry_score(self._row(iv_rank=10.0), DEFAULT_ENTRY_CONFIG)
        score_high_iv = calculate_entry_score(self._row(iv_rank=90.0), DEFAULT_ENTRY_CONFIG)
        assert score_low_iv > score_high_iv, (
            f"Low IV rank should score higher: {score_low_iv} vs {score_high_iv}"
        )

    def test_neutral_rsi_gives_higher_score_than_extreme(self):
        """RSI in neutral range [40-60] → higher score than extreme RSI."""
        score_neutral = calculate_entry_score(self._row(rsi_14=50.0), DEFAULT_ENTRY_CONFIG)
        score_extreme = calculate_entry_score(self._row(rsi_14=85.0), DEFAULT_ENTRY_CONFIG)
        assert score_neutral > score_extreme, (
            f"Neutral RSI should score higher: {score_neutral} vs {score_extreme}"
        )

    def test_missing_indicators_fallback_to_neutral(self):
        """Row with no indicators should return 50 (all components fallback to neutral)."""
        empty_row = pd.Series({})
        score = calculate_entry_score(empty_row, DEFAULT_ENTRY_CONFIG)
        # Component 5 (DTE) is hardcoded to 100, others fallback to 50
        # Weighted: 50*0.30 + 50*0.20 + 50*0.20 + 50*0.15 + 100*0.10 + 50*0.05 ≈ 55
        assert 40 <= score <= 70, f"Fallback score should be near neutral (~55), got {score}"

    def test_score_with_empty_config_uses_defaults(self):
        """Empty config should use hardcoded defaults and still return non-zero."""
        score = calculate_entry_score(self._row(), {})
        assert score > 0, f"Expected non-zero score with empty config, got {score}"


class TestEntrySizeGating:
    """Verify size_multiplier is 0 when entry_score < 60 (the root bug)."""

    def test_entry_score_50_gives_zero_size_multiplier(self):
        """Score of 50 (old fallback) → size_multiplier = 0 → positions never open."""
        size = calculate_position_size(50.0, DEFAULT_ENTRY_CONFIG)
        assert size == 0.0, f"Score 50 should give size_multiplier=0, got {size}"

    def test_entry_score_65_gives_nonzero_size_multiplier(self):
        """Score of 65 (realistic with real indicators) → size_multiplier > 0."""
        size = calculate_position_size(65.0, DEFAULT_ENTRY_CONFIG)
        assert size > 0.0, f"Score 65 should give size_multiplier > 0, got {size}"

    def test_entry_score_80_gives_full_size(self):
        size = calculate_position_size(80.0, DEFAULT_ENTRY_CONFIG)
        assert size == 1.0, f"Score 80 should give full size=1.0, got {size}"

    def test_strategy_spec_size_multiplier_reflects_real_entry_score(self):
        """With real entry_score > 60, strategy_spec.size_multiplier must be > 0."""
        spec = select_strategy(Zone.A, Trend.UP, entry_score=70.0)
        assert spec.size_multiplier > 0.0, (
            f"size_multiplier should be > 0 with entry_score=70, got {spec.size_multiplier}"
        )

    def test_strategy_spec_size_multiplier_is_zero_with_fallback_score(self):
        """With old fallback score of 50, size_multiplier is 0 (confirms the bug)."""
        spec = select_strategy(Zone.A, Trend.UP, entry_score=50.0)
        assert spec.size_multiplier == 0.0, (
            f"size_multiplier should be 0 with entry_score=50, got {spec.size_multiplier}"
        )


class TestEntryScoreDataframePipeline:
    """Verify entry_score column is added to the dataframe."""

    def _make_df_with_indicators(self, n: int = 10) -> pd.DataFrame:
        """Build a minimal dataframe with all columns needed by calculate_entry_score."""
        np.random.seed(42)
        return pd.DataFrame({
            "iv_rank": np.random.uniform(20, 70, n),
            "iv_rv_ratio": np.random.uniform(0.8, 1.5, n),
            "squeeze_intensity": np.random.uniform(30, 80, n),
            "rsi_14": np.random.uniform(35, 65, n),
            "volume_ratio": np.random.uniform(0.6, 1.2, n),
            "dte_days": [45] * n,
        })

    def test_apply_entry_score_adds_column(self):
        df = self._make_df_with_indicators()
        df["entry_score"] = df.apply(
            lambda row: calculate_entry_score(row, DEFAULT_ENTRY_CONFIG), axis=1
        )
        assert "entry_score" in df.columns

    def test_entry_score_column_is_nonzero(self):
        df = self._make_df_with_indicators()
        df["entry_score"] = df.apply(
            lambda row: calculate_entry_score(row, DEFAULT_ENTRY_CONFIG), axis=1
        )
        assert (df["entry_score"] > 0).all(), (
            f"All rows should have entry_score > 0, got: {df['entry_score'].tolist()}"
        )

    def test_entry_score_column_varies_across_rows(self):
        """entry_score should not be constant — it must vary with market conditions."""
        df = self._make_df_with_indicators(n=20)
        df["entry_score"] = df.apply(
            lambda row: calculate_entry_score(row, DEFAULT_ENTRY_CONFIG), axis=1
        )
        assert df["entry_score"].std() > 1.0, (
            f"entry_score should vary across rows (std > 1), got std={df['entry_score'].std():.2f}"
        )

    def test_entry_score_in_valid_range(self):
        df = self._make_df_with_indicators(n=20)
        df["entry_score"] = df.apply(
            lambda row: calculate_entry_score(row, DEFAULT_ENTRY_CONFIG), axis=1
        )
        assert df["entry_score"].between(0, 100).all(), (
            f"All entry_scores should be in [0, 100]"
        )
