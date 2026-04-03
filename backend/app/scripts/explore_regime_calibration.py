"""
Esplorazione delle due alternative per ricalibrare il regime detector.

Alternativa A — Soglie percentili
  Le soglie vengono fissate sui percentili della distribuzione storica del MacroScore
  invece che sui valori assoluti ±0.5. Obiettivo: circa 20% dei mesi per regime.

Alternativa B — Pesi MacroScore
  Si testano combinazioni di pesi diverse per i pillar nel calcolo del MacroScore,
  cercando un segnale più polarizzato (meno cancellazione tra pillar).

Uso:
    docker compose exec backend python -m app.scripts.explore_regime_calibration
"""
from datetime import date

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.db.macro_pillar import MacroPillar
from app.db.session import SessionLocal
from app.services.config_repo import get_macro_score_weights, get_regime_thresholds

# Tutto il periodo disponibile per la distribuzione storica
HISTORY_START = date(2000, 1, 1)
HISTORY_END   = date(2024, 12, 31)

# Training (per la distribuzione)
TRAINING_START = date(2007, 6, 1)
TRAINING_END   = date(2017, 12, 31)

REGIMES_ORDER  = ["Recessione", "Rallentamento", "Ripresa", "Espansione"]

N_SMOOTH = 3  # finestra MA fissa per questo confronto


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_pillar_pivot(db: Session, start: date, end: date) -> pd.DataFrame:
    rows = (
        db.query(MacroPillar)
        .filter(MacroPillar.date >= start, MacroPillar.date <= end)
        .order_by(MacroPillar.date)
        .all()
    )
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([{"date": r.date, "pillar": r.pillar, "score": float(r.score)} for r in rows])
    pivot = df.pivot(index="date", columns="pillar", values="score")
    pivot.index = pd.to_datetime(pivot.index)
    return pivot.resample("ME").last().dropna(how="all")


def compute_macro_score(pivot: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    score = pd.Series(0.0, index=pivot.index)
    for pillar, w in weights.items():
        if pillar in pivot.columns:
            score += pivot[pillar] * w
    return score


def smooth(series: pd.Series, n: int) -> pd.Series:
    return series.rolling(n, min_periods=n).mean().dropna()


def assign_regimes_abs(macro: pd.Series, thresholds: list[tuple]) -> pd.Series:
    sorted_th = sorted(thresholds, key=lambda x: (x[0] is None, x[0] if x[0] is not None else float("-inf")))
    def _detect(s):
        regime = sorted_th[0][1]
        for t, name in sorted_th:
            if t is not None and s >= t:
                regime = name
        return regime
    return macro.apply(_detect)


def assign_regimes_percentile(macro: pd.Series, pct_thresholds: dict[str, float]) -> pd.Series:
    """pct_thresholds: {nome_regime: soglia_valore} già calcolata sui percentili."""
    sorted_th = sorted(pct_thresholds.items(), key=lambda x: x[1])
    def _detect(s):
        regime = sorted_th[0][0]
        for name, t in sorted_th:
            if s >= t:
                regime = name
        return regime
    return macro.apply(_detect)


def distribution_table(regime_series: pd.Series, label: str) -> None:
    counts = regime_series.value_counts()
    total  = len(regime_series)
    print(f"\n  {label}  (MA({N_SMOOTH}), {total} mesi totali)")
    print(f"  {'Regime':<16s}  {'N':>5s}  {'%':>5s}  Barra")
    print(f"  {'-' * 50}")
    for regime in REGIMES_ORDER:
        cnt = counts.get(regime, 0)
        bar = "█" * round(cnt / total * 25)
        print(f"  {regime:<16s}  {cnt:>5d}  {cnt/total:>4.0%}  {bar}")


def score_stats(macro: pd.Series, label: str) -> None:
    print(f"\n  {label}")
    print(f"  Min={macro.min():+.3f}  P10={macro.quantile(0.10):+.3f}  "
          f"P25={macro.quantile(0.25):+.3f}  Median={macro.median():+.3f}  "
          f"P75={macro.quantile(0.75):+.3f}  P90={macro.quantile(0.90):+.3f}  Max={macro.max():+.3f}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"\n{'=' * 68}")
    print(f"  ESPLORAZIONE CALIBRAZIONE REGIMI")
    print(f"{'=' * 68}")

    db = SessionLocal()
    try:
        current_weights = get_macro_score_weights(db)
        thresholds_db   = get_regime_thresholds(db)

        pivot_full     = load_pillar_pivot(db, HISTORY_START, HISTORY_END)
        pivot_training = load_pillar_pivot(db, TRAINING_START, TRAINING_END)

        if pivot_full.empty:
            print("  ERROR: nessun dato macro_pillars")
            return

        print(f"\n  Pesi MacroScore correnti: {current_weights}")
        print(f"  Soglie regime correnti:   {[(t, n) for t, n in thresholds_db]}")
        print(f"\n  Periodo completo: {pivot_full.index.min().date()} → {pivot_full.index.max().date()}")
        print(f"  Periodo training: {pivot_training.index.min().date()} → {pivot_training.index.max().date()}")

        # MacroScore corrente (formula attuale)
        macro_full_raw  = compute_macro_score(pivot_full, current_weights)
        macro_full_sm   = smooth(macro_full_raw, N_SMOOTH)
        macro_train_sm  = smooth(compute_macro_score(pivot_training, current_weights), N_SMOOTH)

        # ─────────────────────────────────────────────────────────────────────
        print(f"\n{'─' * 68}")
        print(f"  STATO ATTUALE — distribuzione MacroScore")
        print(f"{'─' * 68}")
        score_stats(macro_full_sm, f"MacroScore smooth MA({N_SMOOTH}) — periodo completo 2000–2024")
        regime_current = assign_regimes_abs(macro_full_sm, thresholds_db)
        distribution_table(regime_current, "Distribuzione regimi ATTUALE (soglie ±0.5) — 2000–2024")

        regime_train_current = assign_regimes_abs(macro_train_sm, thresholds_db)
        distribution_table(regime_train_current, "Distribuzione regimi ATTUALE (soglie ±0.5) — training 2007–2017")

        # ─────────────────────────────────────────────────────────────────────
        print(f"\n{'─' * 68}")
        print(f"  ALTERNATIVA A — Soglie percentili (su periodo completo 2000–2024)")
        print(f"{'─' * 68}")

        # Target: ~20% Recessione, ~30% Rallentamento, ~30% Ripresa, ~20% Espansione
        targets = [
            ("20/30/30/20", [0.20, 0.50, 0.80]),
            ("15/35/35/15", [0.15, 0.50, 0.85]),
            ("25/25/25/25", [0.25, 0.50, 0.75]),
        ]

        for label, pcts in targets:
            t_rec  = macro_full_sm.quantile(pcts[0])
            t_rall = macro_full_sm.quantile(pcts[1])
            t_ripr = macro_full_sm.quantile(pcts[2])
            thresholds_pct = {
                "Recessione":    float("-inf"),
                "Rallentamento": t_rec,
                "Ripresa":       t_rall,
                "Espansione":    t_ripr,
            }
            print(f"\n  Distribuzione target {label}:")
            print(f"  Soglie calcolate →  Recessione < {t_rec:+.3f}  |  "
                  f"Rallentamento [{t_rec:+.3f}, {t_rall:+.3f})  |  "
                  f"Ripresa [{t_rall:+.3f}, {t_ripr:+.3f})  |  "
                  f"Espansione ≥ {t_ripr:+.3f}")
            regime_a = assign_regimes_percentile(macro_full_sm, thresholds_pct)
            distribution_table(regime_a, f"Distribuzione A-{label} — 2000–2024")
            regime_a_train = assign_regimes_percentile(
                smooth(compute_macro_score(pivot_training, current_weights), N_SMOOTH),
                thresholds_pct,
            )
            distribution_table(regime_a_train, f"Distribuzione A-{label} — training 2007–2017")

        # ─────────────────────────────────────────────────────────────────────
        print(f"\n{'─' * 68}")
        print(f"  ALTERNATIVA B — Ricalibrazione pesi MacroScore")
        print(f"{'─' * 68}")
        print(f"  Soglie fisse ±0.5 invariate. Si varia la formula del MacroScore.")

        weight_scenarios = {
            "Attuale":        {"Growth": 0.30, "Inflation": -0.30, "Policy": -0.20, "Risk": -0.20},
            "Growth+Risk":    {"Growth": 0.50, "Risk": -0.50},
            "Risk amplif.":   {"Growth": 0.25, "Inflation": -0.25, "Policy": -0.10, "Risk": -0.40},
            "No Policy":      {"Growth": 0.40, "Inflation": -0.30, "Risk": -0.30},
            "Solo Growth":    {"Growth": 1.00},
        }

        print(f"\n  {'Scenario':<16s}  {'Min':>6s}  {'Max':>6s}  {'P10':>6s}  {'P90':>6s}  {'StdDev':>7s}")
        print(f"  {'-' * 58}")
        for name, weights in weight_scenarios.items():
            ms  = smooth(compute_macro_score(pivot_full, weights), N_SMOOTH)
            print(f"  {name:<16s}  {ms.min():>+6.3f}  {ms.max():>+6.3f}  "
                  f"{ms.quantile(0.10):>+6.3f}  {ms.quantile(0.90):>+6.3f}  {ms.std():>7.3f}")

        print()
        for name, weights in weight_scenarios.items():
            ms_full  = smooth(compute_macro_score(pivot_full, weights), N_SMOOTH)
            ms_train = smooth(compute_macro_score(pivot_training, weights), N_SMOOTH)
            reg_full  = assign_regimes_abs(ms_full, thresholds_db)
            reg_train = assign_regimes_abs(ms_train, thresholds_db)
            distribution_table(reg_full,  f"B — {name} — 2000–2024 (soglie ±0.5)")
            distribution_table(reg_train, f"B — {name} — training 2007–2017 (soglie ±0.5)")

        # ─────────────────────────────────────────────────────────────────────
        print(f"\n{'─' * 68}")
        print(f"  ALTERNATIVA A+B — Percentili applicati agli scenari B migliori")
        print(f"{'─' * 68}")
        print(f"  Per completezza: distribuzione 20/30/30/20 su Growth+Risk e Risk amplif.")

        for name in ["Growth+Risk", "Risk amplif."]:
            weights = weight_scenarios[name]
            ms_full  = smooth(compute_macro_score(pivot_full, weights), N_SMOOTH)
            ms_train = smooth(compute_macro_score(pivot_training, weights), N_SMOOTH)
            t_rec  = ms_full.quantile(0.20)
            t_rall = ms_full.quantile(0.50)
            t_ripr = ms_full.quantile(0.80)
            thresholds_pct = {
                "Recessione":    float("-inf"),
                "Rallentamento": t_rec,
                "Ripresa":       t_rall,
                "Espansione":    t_ripr,
            }
            print(f"\n  {name} + percentili 20/50/80:")
            print(f"  Soglie → <{t_rec:+.3f}  |  {t_rec:+.3f}÷{t_rall:+.3f}  |  {t_rall:+.3f}÷{t_ripr:+.3f}  |  ≥{t_ripr:+.3f}")
            distribution_table(assign_regimes_percentile(ms_full, thresholds_pct),  f"A+B {name} — 2000–2024")
            distribution_table(assign_regimes_percentile(ms_train, thresholds_pct), f"A+B {name} — training 2007–2017")

    finally:
        db.close()


if __name__ == "__main__":
    main()
