from .base import StrategySpec
from .bull_put import bull_put_strategy
from .bear_call import bear_call_strategy
from .no_trade import no_trade_strategy
from .neutral_broken_wing import neutral_broken_wing_strategy
from .entry_scoring import calculate_entry_score, calculate_position_size
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def _classify_zone(row: pd.Series) -> str:
    """
    Classifica il mercato in una delle 4 zone (A/B/C/D) basata su IV Rank e ADX.

    Schema (Options Engine Framework):
                  IV BASSA (<30%)        IV ALTA (>50%)
    DIREZIONALE   →   ZONA A                 ZONA B
    (ADX > 25)        Long vol + bias        Credit spread dir.

    LATERALE      →   ZONA C                 ZONA D
    (ADX < 25)        Straddle / Strangle    Iron Condor / Short Strangle

    Args:
        row: Series con colonne 'iv_rank' e 'adx'

    Returns:
        str: "A", "B", "C", "D" oppure "UNKNOWN" se dati incompleti
    """
    iv_rank = row.get("iv_rank")
    adx = row.get("adx")

    # Dati incompleti — fallback a logica legacy
    if iv_rank is None or adx is None or pd.isna(iv_rank) or pd.isna(adx):
        return "UNKNOWN"

    iv_rank = float(iv_rank)
    adx = float(adx)

    # Classificazione regime IV
    iv_low = iv_rank < 30
    iv_high = iv_rank > 50

    # Classificazione trend
    trend_directional = adx > 25
    trend_lateral = adx <= 25

    # Assegnazione zone
    if trend_directional and iv_low:
        return "A"  # Breakout setup — long volatility
    elif trend_directional and iv_high:
        return "B"  # Trending con IV alta — credit spreads
    elif trend_lateral and iv_low:
        return "C"  # Squeeze — straddle/strangle
    elif trend_lateral and iv_high:
        return "D"  # Consolidation with high IV — iron condor
    else:
        # Zone intermedie (30% <= IV_rank <= 50% oppure ADX intorno a 25)
        # Fallback a "NEUTRAL"
        return "NEUTRAL"


def select_strategy(row: pd.Series, entry_config: dict) -> StrategySpec:
    """
    Select strategy basata su regime IV/ADX (framework-aware) e segnali tecnici.

    Utilizza IV Rank e ADX per la classificazione (TIER 1 CRITICAL),
    fallback a legacy logic basata su IV/RSI/macro se dati incompleti.

    Ritorna StrategySpec con size_multiplier (0.0-1.0) basato su entry score composito.
    """
    iv = float(row["iv"])
    rsi = row["rsi_14"]
    macro = row["macro_regime"]
    iv_rv_ratio = row["iv_rv_ratio"]
    trend_signal = row["trend_signal"]
    adx = row.get("adx")
    iv_rank = row.get("iv_rank")

    iv_min_threshold = float(entry_config.get("iv_min_threshold", 0.18))
    rsi_min_bull = float(entry_config.get("rsi_min_bull", 40))
    iv_min_neutral = float(entry_config.get("iv_min_neutral", 0.15))
    iv_rv_ratio_min = float(entry_config.get("iv_rv_ratio_min", 1.1))

    # --- Calculate entry score (TIER 1: quality-based sizing) ---
    entry_score = calculate_entry_score(row, entry_config)
    size_multiplier = calculate_position_size(entry_score, entry_config)
    logger.warning(f"[SCORING] entry_score={entry_score:.1f}, size_multiplier={size_multiplier:.0%}")

    # --- Filtro globale IV minima ---
    if iv < iv_min_threshold:
        logger.warning(f"[FILTER] IV too low: {iv:.2f} < {iv_min_threshold:.2f}")
        return no_trade_strategy()

    # --- Regime-aware strategy selection (TIER 1) ---
    zone = _classify_zone(row)

    # ZONA A: Direzionale + IV bassa → Long volatility bias
    # Setup ideale: aspetta breakout da squeeze
    if zone == "A":
        # Long volatility ma con bias direzionale
        if trend_signal == 1:
            spec = bull_put_strategy()
            spec.size_multiplier = size_multiplier
            return spec
        elif trend_signal == -1:
            spec = bear_call_strategy()
            spec.size_multiplier = size_multiplier
            return spec
        else:
            # Trend neutro in zone A (raro) → conservative neutral
            spec = neutral_broken_wing_strategy()
            spec.size_multiplier = size_multiplier
            return spec

    # ZONA B: Direzionale + IV alta → Credit spreads direzionali
    # Setup: profita dal decadimento temporale in trend
    elif zone == "B":
        if trend_signal == 1 and iv_rv_ratio > iv_rv_ratio_min:
            spec = bull_put_strategy()
            spec.size_multiplier = size_multiplier
            return spec
        elif trend_signal == -1 and iv_rv_ratio > iv_rv_ratio_min:
            spec = bear_call_strategy()
            spec.size_multiplier = size_multiplier
            return spec
        else:
            return no_trade_strategy()

    # ZONA C: Laterale + IV bassa → Straddle/Strangle (breakout atteso)
    # Setup: IV compression → aspetta movimento
    elif zone == "C":
        # Volatility expansion attesa
        if macro != "RISK_OFF":
            spec = neutral_broken_wing_strategy()
            spec.size_multiplier = size_multiplier
            return spec
        else:
            return no_trade_strategy()

    # ZONA D: Laterale + IV alta → Iron Condor (vol crush atteso)
    # Setup: incassa premium su stabilità
    elif zone == "D":
        if trend_signal == 0 and iv_rv_ratio > iv_rv_ratio_min:
            spec = neutral_broken_wing_strategy()
            spec.size_multiplier = size_multiplier
            return spec
        else:
            return no_trade_strategy()

    # --- Fallback alla logica legacy (zone UNKNOWN/NEUTRAL) ---
    # Quando IV Rank/ADX non disponibili
    else:
        # Bull put: macro rialzista + trend confermato + IV premium + RSI ok
        if (
            macro == "RISK_ON"
            and trend_signal == 1
            and iv_rv_ratio > iv_rv_ratio_min
            and rsi is not None
            and rsi >= rsi_min_bull
        ):
            spec = bull_put_strategy()
            spec.size_multiplier = size_multiplier
            return spec

        # Bear call: macro ribassista + trend confermato + IV premium
        if (
            macro == "RISK_OFF"
            and trend_signal == -1
            and iv_rv_ratio > iv_rv_ratio_min
        ):
            spec = bear_call_strategy()
            spec.size_multiplier = size_multiplier
            return spec

        # Neutral: nessun trend chiaro + IV sufficiente + macro non in stress
        if (
            trend_signal == 0
            and iv >= iv_min_neutral
            and macro != "RISK_OFF"
        ):
            spec = neutral_broken_wing_strategy()
            spec.size_multiplier = size_multiplier
            return spec

        return no_trade_strategy()
