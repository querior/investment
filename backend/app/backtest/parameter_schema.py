"""
Parameter schema for backtest runs.
Defines valid ranges, types, and defaults for all configurable parameters.
"""

from typing import TypedDict, Any


class ParameterDef(TypedDict, total=False):
    """Definition of a single parameter"""
    type: str              # "float", "bool", "int", "string"
    min: float
    max: float
    default: str
    unit: str             # "value", "pct", "days", "ratio"
    precision: int        # decimal places for numeric inputs


PARAMETER_SCHEMA: dict[str, ParameterDef] = {
    # =========================================================================
    # ENTRY PARAMETERS
    # =========================================================================
    "entry.iv_min_threshold": {
        "type": "float",
        "min": 0.0,
        "max": 1.0,
        "default": "0.18",
        "unit": "value",
        "precision": 2,
    },
    "entry.rsi_min_bull": {
        "type": "float",
        "min": 0.0,
        "max": 100.0,
        "default": "40",
        "unit": "value",
        "precision": 0,
    },
    "entry.iv_min_neutral": {
        "type": "float",
        "min": 0.0,
        "max": 1.0,
        "default": "0.15",
        "unit": "value",
        "precision": 2,
    },
    "entry.iv_rv_ratio_min": {
        "type": "float",
        "min": 0.0,
        "default": "1.1",
        "unit": "ratio",
        "precision": 1,
    },
    "entry.target_delta_short": {
        "type": "float",
        "min": 0.0,
        "max": 1.0,
        "default": "0.16",
        "unit": "value",
        "precision": 2,
    },
    "entry.target_delta_long": {
        "type": "float",
        "min": 0.0,
        "max": 1.0,
        "default": "0.05",
        "unit": "value",
        "precision": 2,
    },
    "entry.cooldown_days": {
        "type": "int",
        "min": 0,
        "max": 30,
        "default": "5",
        "unit": "days",
        "precision": 0,
    },

    # =========================================================================
    # ENTRY SCORING PARAMETERS (Quality-Based Sizing)
    # =========================================================================
    "entry_score.w1_iv_rank": {
        "type": "float",
        "min": 0.0,
        "max": 1.0,
        "default": "0.30",
        "unit": "ratio",
        "precision": 2,
    },
    "entry_score.w2_iv_hv": {
        "type": "float",
        "min": 0.0,
        "max": 1.0,
        "default": "0.20",
        "unit": "ratio",
        "precision": 2,
    },
    "entry_score.w3_squeeze": {
        "type": "float",
        "min": 0.0,
        "max": 1.0,
        "default": "0.20",
        "unit": "ratio",
        "precision": 2,
    },
    "entry_score.w4_rsi": {
        "type": "float",
        "min": 0.0,
        "max": 1.0,
        "default": "0.15",
        "unit": "ratio",
        "precision": 2,
    },
    "entry_score.w5_dte": {
        "type": "float",
        "min": 0.0,
        "max": 1.0,
        "default": "0.10",
        "unit": "ratio",
        "precision": 2,
    },
    "entry_score.w6_volume": {
        "type": "float",
        "min": 0.0,
        "max": 1.0,
        "default": "0.05",
        "unit": "ratio",
        "precision": 2,
    },
    "entry_size.threshold_full": {
        "type": "float",
        "min": 0.0,
        "max": 100.0,
        "default": "75",
        "unit": "value",
        "precision": 0,
    },
    "entry_size.threshold_reduced": {
        "type": "float",
        "min": 0.0,
        "max": 100.0,
        "default": "60",
        "unit": "value",
        "precision": 0,
    },
    "entry_size.multiplier_full": {
        "type": "float",
        "min": 0.0,
        "max": 1.0,
        "default": "1.0",
        "unit": "value",
        "precision": 2,
    },
    "entry_size.multiplier_reduced": {
        "type": "float",
        "min": 0.0,
        "max": 1.0,
        "default": "0.75",
        "unit": "value",
        "precision": 2,
    },

    # =========================================================================
    # ENTRY SCORING PARAMETERS — DTE Optimal Range
    # =========================================================================
    "entry_score.dte_min": {
        "type": "int",
        "min": 1,
        "max": 100,
        "default": "21",
        "unit": "days",
        "precision": 0,
    },
    "entry_score.dte_optimal_min": {
        "type": "int",
        "min": 1,
        "max": 100,
        "default": "35",
        "unit": "days",
        "precision": 0,
    },
    "entry_score.dte_optimal_max": {
        "type": "int",
        "min": 1,
        "max": 100,
        "default": "45",
        "unit": "days",
        "precision": 0,
    },
    "entry_score.dte_max": {
        "type": "int",
        "min": 1,
        "max": 365,
        "default": "55",
        "unit": "days",
        "precision": 0,
    },

    # =========================================================================
    # ENTRY SCORING PARAMETERS — RSI Neutrality
    # =========================================================================
    "entry_score.rsi_neutral_min": {
        "type": "float",
        "min": 0.0,
        "max": 100.0,
        "default": "40",
        "unit": "value",
        "precision": 0,
    },
    "entry_score.rsi_neutral_max": {
        "type": "float",
        "min": 0.0,
        "max": 100.0,
        "default": "60",
        "unit": "value",
        "precision": 0,
    },

    # =========================================================================
    # EXIT PARAMETERS — DTE Rule
    # =========================================================================
    "exit.rule_dte.enabled": {
        "type": "bool",
        "default": "true",
        "unit": "value",
    },
    "exit.rule_dte.threshold_days": {
        "type": "float",
        "min": 1.0,
        "max": 365.0,
        "default": "21",
        "unit": "days",
        "precision": 0,
    },

    # =========================================================================
    # EXIT PARAMETERS — Profit Target Rule
    # =========================================================================
    "exit.rule_profit_target.enabled": {
        "type": "bool",
        "default": "true",
        "unit": "value",
    },
    "exit.rule_profit_target.threshold_pct": {
        "type": "float",
        "min": 0.0,
        "max": 100.0,
        "default": "50",
        "unit": "pct",
        "precision": 0,
    },

    # =========================================================================
    # EXIT PARAMETERS — Stop Loss Rule
    # =========================================================================
    "exit.rule_stop_loss.enabled": {
        "type": "bool",
        "default": "true",
        "unit": "value",
    },
    "exit.rule_stop_loss.threshold_pct": {
        "type": "float",
        "min": 0.0,
        "default": "200",
        "unit": "pct",
        "precision": 0,
    },

    # =========================================================================
    # EXIT PARAMETERS — Trailing Stop Rule
    # =========================================================================
    "exit.rule_trailing_stop.enabled": {
        "type": "bool",
        "default": "false",
        "unit": "value",
    },
    "exit.rule_trailing_stop.min_profit_pct": {
        "type": "float",
        "min": 0.0,
        "max": 100.0,
        "default": "30",
        "unit": "pct",
        "precision": 0,
    },
    "exit.rule_trailing_stop.pullback_pct": {
        "type": "float",
        "min": 0.0,
        "max": 100.0,
        "default": "15",
        "unit": "pct",
        "precision": 0,
    },

    # =========================================================================
    # EXIT PARAMETERS — Macro Reversal Rule
    # =========================================================================
    "exit.rule_macro_reversal.enabled": {
        "type": "bool",
        "default": "true",
        "unit": "value",
    },

    # =========================================================================
    # EXIT PARAMETERS — Momentum Reversal Rule
    # =========================================================================
    "exit.rule_momentum_reversal.enabled": {
        "type": "bool",
        "default": "true",
        "unit": "value",
    },
    "exit.rule_momentum_reversal.rsi_threshold": {
        "type": "float",
        "min": 0.0,
        "max": 100.0,
        "default": "30",
        "unit": "value",
        "precision": 0,
    },
    "exit.rule_momentum_reversal.use_macd": {
        "type": "bool",
        "default": "true",
        "unit": "value",
    },

    # =========================================================================
    # EXIT PARAMETERS — IV Spike Rule
    # =========================================================================
    "exit.rule_iv_spike.enabled": {
        "type": "bool",
        "default": "false",
        "unit": "value",
    },
    "exit.rule_iv_spike.threshold_ratio": {
        "type": "float",
        "min": 0.0,
        "default": "2.0",
        "unit": "ratio",
        "precision": 1,
    },

    # =========================================================================
    # EXIT PARAMETERS — Delta Breach Rule
    # =========================================================================
    "exit.rule_delta_breach.enabled": {
        "type": "bool",
        "default": "false",
        "unit": "value",
    },
    "exit.rule_delta_breach.threshold": {
        "type": "float",
        "min": 0.0,
        "max": 1.0,
        "default": "0.50",
        "unit": "value",
        "precision": 2,
    },

    # =========================================================================
    # EXIT PARAMETERS — Theta Decay Rule
    # =========================================================================
    "exit.rule_theta_decay.enabled": {
        "type": "bool",
        "default": "false",
        "unit": "value",
    },
    "exit.rule_theta_decay.threshold_ratio": {
        "type": "float",
        "min": 0.0,
        "default": "0.05",
        "unit": "ratio",
        "precision": 2,
    },

    # =========================================================================
    # STRATEGY PARAMETERS
    # =========================================================================
    "strategy.initial_allocation": {
        "type": "string",
        "default": "neutral",
        "unit": "value",
    },
    "strategy.coherence_factor": {
        "type": "float",
        "min": 0.0,
        "max": 1.0,
        "default": "0.5",
        "unit": "value",
        "precision": 2,
    },
    "strategy.allocation_alpha": {
        "type": "float",
        "min": 0.0,
        "max": 1.0,
        "default": "0.3",
        "unit": "value",
        "precision": 2,
    },

    # =========================================================================
    # RISK PARAMETERS
    # =========================================================================
    "max_risk": {
        "type": "float",
        "min": 0.0,
        "max": 100.0,
        "default": "0.03",
        "unit": "pct",
        "precision": 2,
    },

    # =========================================================================
    # PIPELINE PARAMETERS (Indicators Calculation)
    # =========================================================================
    "iv_rank.lookback_days": {
        "type": "int",
        "min": 30,
        "max": 365,
        "default": "252",
        "unit": "days",
        "precision": 0,
    },
    "adx.period": {
        "type": "int",
        "min": 5,
        "max": 50,
        "default": "14",
        "unit": "value",
        "precision": 0,
    },
    "squeeze.bb_percentile": {
        "type": "int",
        "min": 5,
        "max": 50,
        "default": "20",
        "unit": "value",
        "precision": 0,
    },
    "squeeze.macd_threshold": {
        "type": "float",
        "min": 0.0,
        "max": 10.0,
        "default": "0.5",
        "unit": "value",
        "precision": 2,
    },
    "volume.sma_period": {
        "type": "int",
        "min": 5,
        "max": 100,
        "default": "20",
        "unit": "days",
        "precision": 0,
    },
    "alpha_volatility": {
        "type": "float",
        "min": 0.0,
        "max": 10.0,
        "default": "4.0",
        "unit": "value",
        "precision": 1,
    },
    "iv_min": {
        "type": "float",
        "min": 0.0,
        "max": 1.0,
        "default": "0.10",
        "unit": "value",
        "precision": 2,
    },
    "iv_max": {
        "type": "float",
        "min": 0.0,
        "max": 2.0,
        "default": "0.80",
        "unit": "value",
        "precision": 2,
    },

    # =========================================================================
    # GLOBAL/HEADER PARAMETERS
    # =========================================================================
    "symbol": {
        "type": "string",
        "default": "IWM",
        "unit": "value",
    },
    "initial_capital": {
        "type": "float",
        "min": 100.0,
        "default": "10000",
        "unit": "value",
        "precision": 0,
    },
    "entry_every_n_days": {
        "type": "int",
        "min": 1,
        "max": 252,
        "default": "30",
        "unit": "days",
        "precision": 0,
    },
    "ticker": {
        "type": "string",
        "default": "IWM",
        "unit": "value",
    },
}


def validate_parameters(params: dict[str, str]) -> list[str]:
    """
    Validates a dictionary of parameters against the schema.
    Returns a list of validation errors (empty if valid).

    Args:
        params: Dictionary of parameter key-value pairs to validate

    Returns:
        List of error strings. Empty list if all parameters are valid.
    """
    errors = []

    for key, value in params.items():
        # Skip unknown parameters (may be legacy)
        if key not in PARAMETER_SCHEMA:
            continue

        schema = PARAMETER_SCHEMA[key]
        param_type = schema.get("type", "string")

        # Type validation
        if param_type == "bool":
            if value.lower() not in ("true", "false"):
                errors.append(
                    f"'{key}': expected boolean (true/false), got '{value}'"
                )
            continue

        elif param_type == "string":
            # String parameters: just check non-empty
            if not value.strip():
                errors.append(f"'{key}': string cannot be empty")
            continue

        elif param_type in ("float", "int"):
            # Numeric validation
            try:
                float_val = float(value)
            except ValueError:
                errors.append(
                    f"'{key}': expected numeric value, got '{value}'"
                )
                continue

            # Range validation
            if "min" in schema and float_val < schema["min"]:
                min_val = schema["min"]
                errors.append(
                    f"'{key}': must be >= {min_val}, got {float_val}"
                )

            if "max" in schema and float_val > schema["max"]:
                max_val = schema["max"]
                errors.append(
                    f"'{key}': must be <= {max_val}, got {float_val}"
                )

    return errors


def get_parameter_default(key: str) -> str | None:
    """Returns the default value for a parameter, or None if not found."""
    schema = PARAMETER_SCHEMA.get(key)
    if schema:
        return schema.get("default")
    return None


def get_parameter_info(key: str) -> ParameterDef | None:
    """Returns the schema definition for a parameter."""
    return PARAMETER_SCHEMA.get(key)
