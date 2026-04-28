"""
Entry Scoring Module — Qualità della posizione all'ingresso.

Framework: Options Engine Framework, sezione 5
Computo un score composito da 0 a 100 basato su sei fattori:
- IV Rank (driver primario regime)
- IV/HV Ratio (cheap vs expensive)
- Squeeze intensity (BB compression setup)
- RSI neutrality (momentum condition)
- DTE score (timing ottimale)
- Volume ratio (liquidity/volatility compression)

Soglie di size:
- > 75: full size (100%)
- 60–74: reduced size (75%)
- < 60: no entry (0%)
"""

import pandas as pd
import numpy as np


def calculate_entry_score(row: pd.Series, entry_config: dict) -> float:
    """
    Calculate composite entry quality score (0-100).

    Formula:
    Q = w1*(100 - IV_rank) + w2*(1 - IV/HV) + w3*squeeze + w4*rsi_neut + w5*dte + w6*vol_ratio

    Args:
        row: Market data row with all required indicators
        entry_config: Entry configuration dict (weights, thresholds, DTE params)

    Returns:
        float: Entry score 0-100
    """
    # --- Extract weights from config (defaults match framework) ---
    w1 = float(entry_config.get("entry_score.w1_iv_rank", 0.30))
    w2 = float(entry_config.get("entry_score.w2_iv_hv", 0.20))
    w3 = float(entry_config.get("entry_score.w3_squeeze", 0.20))
    w4 = float(entry_config.get("entry_score.w4_rsi", 0.15))
    w5 = float(entry_config.get("entry_score.w5_dte", 0.10))
    w6 = float(entry_config.get("entry_score.w6_volume", 0.05))

    # Normalize weights to sum = 1
    total_weight = w1 + w2 + w3 + w4 + w5 + w6
    if total_weight == 0:
        total_weight = 1.0
    w1 /= total_weight
    w2 /= total_weight
    w3 /= total_weight
    w4 /= total_weight
    w5 /= total_weight
    w6 /= total_weight

    # --- Component 1: IV Rank (0-100, already normalized) ---
    iv_rank = row.get("iv_rank")
    if iv_rank is None or pd.isna(iv_rank):
        component_1 = 50  # fallback to neutral
    else:
        iv_rank = float(iv_rank)
        component_1 = 100 - iv_rank  # high iv_rank (expensive) → low score

    # --- Component 2: IV/HV Ratio (cheap vs expensive) ---
    # 1 - (IV/HV) means: ratio < 1.0 → score > 0 (good), ratio > 1.0 → score < 0 (bad)
    iv_hv_ratio = row.get("iv_rv_ratio")  # using RV as proxy for HV
    if iv_hv_ratio is None or pd.isna(iv_hv_ratio):
        component_2 = 50
    else:
        iv_hv_ratio = float(iv_hv_ratio)
        # Normalized to 0-100: 1 - ratio → clip to -1..+1, scale to 0-100
        raw_score = 1 - iv_hv_ratio
        component_2 = max(0, min(100, (raw_score + 1) * 50))  # maps [-1,1] to [0,100]

    # --- Component 3: Squeeze Intensity (0-100, BB width percentile) ---
    squeeze_intensity = row.get("squeeze_intensity")
    if squeeze_intensity is None or pd.isna(squeeze_intensity):
        component_3 = 50
    else:
        component_3 = float(squeeze_intensity)  # already 0-100

    # --- Component 4: RSI Neutrality (RSI in middle range is best) ---
    # Best: RSI in neutral range (configurable, default 40-60)
    # Worst: RSI in extreme zones
    rsi_neutral_min = float(entry_config.get("entry_score.rsi_neutral_min", 40))
    rsi_neutral_max = float(entry_config.get("entry_score.rsi_neutral_max", 60))

    rsi = row.get("rsi_14")
    if rsi is None or pd.isna(rsi):
        component_4 = 50
    else:
        rsi = float(rsi)
        # Score logic:
        # - Inside neutral range [40,60]: score peaks at 100
        # - Outside but within [20,80]: score decays linearly to ~30
        # - Extreme [0,20] or [80,100]: score near 0
        if rsi_neutral_min <= rsi <= rsi_neutral_max:
            # Inside neutral range: score 100
            component_4 = 100
        elif (rsi >= 20 and rsi < rsi_neutral_min) or (rsi > rsi_neutral_max and rsi <= 80):
            # Semi-extreme: linear decay
            if rsi < rsi_neutral_min:
                distance = rsi_neutral_min - rsi
                component_4 = 100 - (distance / (rsi_neutral_min - 20)) * 70  # decay to ~30
            else:
                distance = rsi - rsi_neutral_max
                component_4 = 100 - (distance / (80 - rsi_neutral_max)) * 70  # decay to ~30
        else:
            # Extreme: score near 0
            component_4 = 10

    # --- Component 5: DTE Score (Days to Expiration optimal range) ---
    # Optimal: 35-45 DTE. Outside 21-55: suboptimal
    dte_min = int(entry_config.get("entry_score.dte_min", 21))
    dte_optimal_min = int(entry_config.get("entry_score.dte_optimal_min", 35))
    dte_optimal_max = int(entry_config.get("entry_score.dte_optimal_max", 45))
    dte_max = int(entry_config.get("entry_score.dte_max", 55))

    # DTE is fixed in strategy builder (45 days), so this is informational
    # If you want dynamic DTE based on entry conditions, calculate here
    # For now: assume entry always uses 45 DTE → score 100
    component_5 = 100  # or 0-100 based on time_to_entry if adding adaptive DTE

    # --- Component 6: Volume Ratio (compression indicates setup) ---
    # volume_ratio = volume_current / volume_sma_20
    # Low ratio (< 0.7) = vol contraction (setup). High (> 1.5) = vol expansion (noise)
    volume_ratio = row.get("volume_ratio")
    if volume_ratio is None or pd.isna(volume_ratio):
        component_6 = 50
    else:
        volume_ratio = float(volume_ratio)
        # Ideal: ratio between 0.7 and 1.0. Score peaks at 1.0, decays away
        if volume_ratio <= 0.5:
            component_6 = 30  # too low volume
        elif volume_ratio <= 1.0:
            component_6 = 50 + (volume_ratio - 0.5) * 100  # 50-100 as ratio goes 0.5→1.0
        elif volume_ratio <= 1.5:
            component_6 = max(50, 100 - (volume_ratio - 1.0) * 100)  # 100→50 as ratio goes 1.0→1.5
        else:
            component_6 = 30  # too high volume (expansion phase)

    # --- Composite Score ---
    score = (
        w1 * component_1
        + w2 * component_2
        + w3 * component_3
        + w4 * component_4
        + w5 * component_5
        + w6 * component_6
    )

    return float(np.clip(score, 0, 100))


def calculate_position_size(entry_score: float, size_config: dict) -> float:
    """
    Convert entry score to position size multiplier (0.0 to 1.0).

    Framework:
    - Score > 75: full size (1.0)
    - Score 60-74: reduced size (0.75)
    - Score < 60: no entry (0.0)

    Args:
        entry_score: Entry quality score (0-100)
        size_config: Size configuration dict

    Returns:
        float: Size multiplier (0.0 to 1.0)
    """
    threshold_full = float(size_config.get("entry_size.threshold_full", 75))
    threshold_reduced = float(size_config.get("entry_size.threshold_reduced", 60))
    size_reduced = float(size_config.get("entry_size.multiplier_reduced", 0.75))
    size_full = float(size_config.get("entry_size.multiplier_full", 1.0))

    if entry_score > threshold_full:
        return size_full  # 100%
    elif entry_score >= threshold_reduced:
        # Linear interpolation between reduced and full
        return size_reduced + (entry_score - threshold_reduced) / (
            threshold_full - threshold_reduced
        ) * (size_full - size_reduced)
    else:
        return 0.0  # No entry
