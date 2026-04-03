"""
Calibrazione empirica della matrice di sensibilità via Information Coefficient.

Per ogni coppia (pillar, asset) calcola la correlazione di Pearson tra
pillar_score[t] e asset_return[t+1] (no look-ahead) sul periodo di training.

Uso (read-only):
    docker compose exec backend python -m app.scripts.calibrate_sensitivity

Periodo custom:
    docker compose exec backend python -m app.scripts.calibrate_sensitivity --start 2008-01-01 --end 2017-12-31
"""
import argparse
from datetime import date

import numpy as np
import pandas as pd
from scipy import stats
from sqlalchemy.orm import Session

from app.backtest.loaders import load_asset_returns
from app.db.macro_pillar import MacroPillar
from app.db.session import SessionLocal
from app.services.config_repo import get_sensitivity

# Periodo di training di default: inizio dati DBC/BIL → fine 2017
TRAINING_START = date(2007, 6, 1)
TRAINING_END   = date(2017, 12, 31)

PILLARS = ["Growth", "Inflation", "Policy", "Risk"]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_pillar_df(db: Session, start: date, end: date) -> pd.DataFrame:
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


def load_returns_df(db: Session, start: date, end: date) -> pd.DataFrame:
    returns = load_asset_returns(db, start, end, frequency="EOM")
    if not returns:
        return pd.DataFrame()
    records = [{"date": d, **r} for d, r in returns.items()]
    df = pd.DataFrame(records).set_index("date")
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


# ---------------------------------------------------------------------------
# IC computation
# ---------------------------------------------------------------------------

def compute_ic_matrix(
    pillars_df: pd.DataFrame,
    returns_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Returns (IC, p-values, n_obs) — tutti con forma (pillar × asset).

    Coppia: signal[t]  →  return[t+1]
    """
    assets = returns_df.columns.tolist()
    ic_rows, pval_rows, n_rows = {}, {}, {}

    for pillar in PILLARS:
        if pillar not in pillars_df.columns:
            continue
        ic_rows[pillar] = {}
        pval_rows[pillar] = {}
        n_rows[pillar] = {}

        for asset in assets:
            merged = pd.concat(
                [pillars_df[pillar].rename("signal"), returns_df[asset].rename("ret")],
                axis=1,
            ).dropna()

            if len(merged) < 12:
                ic_rows[pillar][asset] = float("nan")
                pval_rows[pillar][asset] = float("nan")
                n_rows[pillar][asset] = len(merged)
                continue

            sig = merged["signal"].values[:-1]   # t
            ret = merged["ret"].values[1:]        # t+1

            r, p = stats.pearsonr(sig, ret)
            ic_rows[pillar][asset] = r
            pval_rows[pillar][asset] = p
            n_rows[pillar][asset] = len(sig)

    ic_df   = pd.DataFrame(ic_rows).T
    pval_df = pd.DataFrame(pval_rows).T
    n_df    = pd.DataFrame(n_rows).T
    return ic_df, pval_df, n_df


def scale_ic(ic_df: pd.DataFrame, target_max: float = 1.0) -> pd.DataFrame:
    """Per ogni pillar, scala la riga affinché max(|IC|) = target_max."""
    out = ic_df.copy()
    for pillar in out.index:
        row_max = out.loc[pillar].abs().max()
        if row_max > 1e-9:
            out.loc[pillar] = out.loc[pillar] / row_max * target_max
    return out


# ---------------------------------------------------------------------------
# Printing
# ---------------------------------------------------------------------------

def _print_matrix(df: pd.DataFrame, title: str, fmt: str = "{:+7.3f}") -> None:
    assets = df.columns.tolist()
    w = max(len(a) for a in assets) + 2
    print(f"\n  {'─' * (12 + w * len(assets))}")
    print(f"  {title}")
    print(f"  {'─' * (12 + w * len(assets))}")
    header = f"  {'':12s}" + "".join(f"{a:>{w}s}" for a in assets)
    print(header)
    for pillar in df.index:
        row = "".join(fmt.format(v) if not np.isnan(v) else f"{'nan':>{w}s}" for v in df.loc[pillar])
        print(f"  {pillar:<12s}{row}")


def _significance_marker(p: float) -> str:
    if np.isnan(p):
        return "   "
    if p < 0.01:
        return "***"
    if p < 0.05:
        return "** "
    if p < 0.10:
        return "*  "
    return "   "


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Calibrazione matrice di sensibilità (read-only)")
    parser.add_argument("--start", default=str(TRAINING_START), help="Data inizio training (YYYY-MM-DD)")
    parser.add_argument("--end",   default=str(TRAINING_END),   help="Data fine training (YYYY-MM-DD)")
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end   = date.fromisoformat(args.end)

    print(f"\n{'=' * 62}")
    print(f"  CALIBRAZIONE MATRICE — training {start} → {end}")
    print(f"{'=' * 62}")

    db = SessionLocal()
    try:
        pillars_df = load_pillar_df(db, start, end)
        returns_df = load_returns_df(db, start, end)

        if pillars_df.empty:
            print("  ERROR: nessun dato macro_pillars nel periodo selezionato")
            return
        if returns_df.empty:
            print("  ERROR: nessun dato market_prices nel periodo selezionato")
            return

        print(f"\n  Pillar data : {len(pillars_df)} mesi  "
              f"({pillars_df.index.min().date()} → {pillars_df.index.max().date()})")
        print(f"  Return data : {len(returns_df)} mesi  "
              f"({returns_df.index.min().date()} → {returns_df.index.max().date()})")
        print(f"  Assets      : {', '.join(returns_df.columns.tolist())}")

        ic_df, pval_df, n_df = compute_ic_matrix(pillars_df, returns_df)
        scaled_df = scale_ic(ic_df, target_max=1.0)

        # Matrice attuale dal DB
        current = get_sensitivity(db)
        assets = returns_df.columns.tolist()
        current_df = pd.DataFrame(
            {asset: {p: current.get(p, {}).get(asset, 0.0) for p in PILLARS} for asset in assets},
        )

        _print_matrix(current_df, "MATRICE ATTUALE (intuizione)")
        _print_matrix(ic_df,      "IC RAW — Pearson r  [pillar[t] → return[t+1]]")
        _print_matrix(pval_df,    "P-VALUES", fmt="{:+7.3f}")
        _print_matrix(n_df,       "N osservazioni", fmt="{:7.0f} ")
        _print_matrix(scaled_df,  "IC SCALATO — max|IC|=1.0 per pillar (candidato matrice)")

        # Confronto affiancato con significatività
        print(f"\n  {'═' * 62}")
        print(f"  CONFRONTO ATTUALE vs CALIBRATO")
        print(f"  {'═' * 62}")
        print(f"  {'':12s}  {'Asset':<12s}  {'Attuale':>8s}  {'Calibrato':>9s}  {'Sig':3s}  {'Δ':>6s}")
        print(f"  {'-' * 58}")
        for pillar in PILLARS:
            if pillar not in ic_df.index:
                continue
            print(f"\n  {pillar}")
            for asset in assets:
                cur = current_df.loc[pillar, asset] if pillar in current_df.index else 0.0
                cal = scaled_df.loc[pillar, asset] if pillar in scaled_df.index else float("nan")
                sig = _significance_marker(pval_df.loc[pillar, asset])
                if not np.isnan(cal):
                    delta = cal - cur
                    arrow = "↑" if delta > 0.05 else ("↓" if delta < -0.05 else "≈")
                    print(f"    {asset:<12s}  {cur:+8.2f}  {cal:+9.3f}  {sig}  {delta:+6.3f} {arrow}")
                else:
                    print(f"    {asset:<12s}  {cur:+8.2f}  {'nan':>9s}  {sig}")

        print(f"\n  Legenda: *** p<0.01  ** p<0.05  * p<0.10")
        print(f"\n  Per applicare la matrice al DB aggiungere il flag --apply (non ancora implementato)")
        print()

    finally:
        db.close()


if __name__ == "__main__":
    main()
