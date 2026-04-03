"""
Calibrazione empirica dei portafogli per regime.

Per ogni finestra di smoothing N (2, 3, 4 mesi), calcola MacroScore_smooth,
assegna ogni mese a un regime e trova il portafoglio che massimizza lo Sharpe
Ratio sui mesi di quel regime (ottimizzazione mean-variance, long-only).

Uso (read-only):
    docker compose exec backend python -m app.scripts.calibrate_regime_portfolios

Periodo custom:
    docker compose exec backend python -m app.scripts.calibrate_regime_portfolios --start 2007-06-01 --end 2017-12-31
"""
import argparse
from datetime import date

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sqlalchemy.orm import Session

from app.backtest.loaders import load_asset_returns
from app.db.macro_pillar import MacroPillar
from app.db.session import SessionLocal
from app.services.config_repo import get_macro_score_weights, get_regime_thresholds

TRAINING_START = date(2007, 6, 1)
TRAINING_END   = date(2017, 12, 31)

REGIMES_ORDER  = ["Recessione", "Rallentamento", "Ripresa", "Espansione"]

RISK_FREE_MONTHLY = 0.0  # approssimazione

# Vincoli per asset per regime: (min, max)
# Espansione → più Equity, meno Bond
# Recessione → più Bond, meno Equity
REGIME_BOUNDS: dict[str, dict[str, tuple[float, float]]] = {
    "Recessione": {
        "Equity":      (0.05, 0.25),
        "Bond":        (0.35, 0.70),
        "Commodities": (0.05, 0.20),
        "Cash":        (0.05, 0.40),
    },
    "Rallentamento": {
        "Equity":      (0.05, 0.50),
        "Bond":        (0.15, 0.60),
        "Commodities": (0.05, 0.30),
        "Cash":        (0.05, 0.40),
    },
    "Ripresa": {
        "Equity":      (0.10, 0.65),
        "Bond":        (0.10, 0.55),
        "Commodities": (0.05, 0.35),
        "Cash":        (0.05, 0.35),
    },
    "Espansione": {
        "Equity":      (0.20, 0.80),
        "Bond":        (0.05, 0.45),
        "Commodities": (0.05, 0.35),
        "Cash":        (0.05, 0.30),
    },
}
# Fallback per regimi non specificati
DEFAULT_BOUNDS: dict[str, tuple[float, float]] = {
    "Equity": (0.05, 0.70), "Bond": (0.10, 0.60),
    "Commodities": (0.05, 0.35), "Cash": (0.05, 0.40),
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_macro_score_series(db: Session, start: date, end: date,
                             score_weights: dict[str, float]) -> pd.Series:
    rows = (
        db.query(MacroPillar)
        .filter(MacroPillar.date >= start, MacroPillar.date <= end)
        .order_by(MacroPillar.date)
        .all()
    )
    if not rows:
        return pd.Series(dtype=float)

    df = pd.DataFrame([{"date": r.date, "pillar": r.pillar, "score": float(r.score)} for r in rows])
    pivot = df.pivot(index="date", columns="pillar", values="score")
    pivot.index = pd.to_datetime(pivot.index)
    pivot = pivot.resample("ME").last().dropna(how="all")

    macro = pd.Series(0.0, index=pivot.index)
    for pillar, w in score_weights.items():
        if pillar in pivot.columns:
            macro += pivot[pillar] * w
    return macro


def load_returns_df(db: Session, start: date, end: date) -> pd.DataFrame:
    returns = load_asset_returns(db, start, end, frequency="EOM")
    if not returns:
        return pd.DataFrame()
    records = [{"date": d, **r} for d, r in returns.items()]
    df = pd.DataFrame(records).set_index("date")
    df.index = pd.to_datetime(df.index)
    return df.sort_index()


# ---------------------------------------------------------------------------
# Regime detection
# ---------------------------------------------------------------------------

def detect_regime(score: float, thresholds: list[tuple]) -> str:
    """
    thresholds: lista di (threshold_min, nome_regime).
    Recessione ha threshold_min = None (nessun lower bound = regime più basso).
    """
    # Default: il regime senza lower bound (Recessione)
    default_regime = next((name for t, name in thresholds if t is None), "Recessione")
    # Soglie non-None in ordine crescente
    sorted_th = sorted([(t, n) for t, n in thresholds if t is not None], key=lambda x: x[0])
    regime = default_regime
    for threshold_min, name in sorted_th:
        if score >= threshold_min:
            regime = name
    return regime


def assign_regimes(macro_smooth: pd.Series, thresholds: list[tuple]) -> pd.Series:
    return macro_smooth.apply(lambda s: detect_regime(s, thresholds))


# ---------------------------------------------------------------------------
# Portfolio optimization
# ---------------------------------------------------------------------------

def max_sharpe_portfolio(returns_df: pd.DataFrame, assets: list[str],
                          regime: str = "") -> dict[str, float]:
    """
    Trova i pesi che massimizzano lo Sharpe Ratio annualizzato sui mesi forniti.
    Vincoli: long-only, sum=1, cap e floor per asset (dipendono dal regime).
    """
    ret = returns_df[assets].dropna()
    n = len(assets)

    regime_b = REGIME_BOUNDS.get(regime, {})

    def _bounds(a: str) -> tuple[float, float]:
        if a in regime_b:
            return regime_b[a]
        return DEFAULT_BOUNDS.get(a, (0.0, 1.0))

    if len(ret) < 6:
        # Troppo pochi mesi: distribuisci rispettando i floor/cap
        lo = np.array([_bounds(a)[0] for a in assets])
        return {a: float(lo[i] + (1.0 - lo.sum()) / n) for i, a in enumerate(assets)}

    mu = ret.mean().values          # rendimento medio mensile
    cov = ret.cov().values          # matrice di covarianza mensile

    def neg_sharpe(w):
        port_ret = np.dot(w, mu) - RISK_FREE_MONTHLY
        port_vol = np.sqrt(np.dot(w, np.dot(cov, w)))
        if port_vol < 1e-10:
            return 0.0
        return -port_ret / port_vol * np.sqrt(12)  # annualizzato

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bounds = [_bounds(a) for a in assets]
    lo = np.array([b[0] for b in bounds])
    w0 = lo + (1.0 - lo.sum()) / n  # start rispettando i floor

    result = minimize(neg_sharpe, w0, method="SLSQP",
                      bounds=bounds, constraints=constraints,
                      options={"ftol": 1e-9, "maxiter": 1000})

    if result.success:
        w = result.x
        w = np.clip(w, [b[0] for b in bounds], [b[1] for b in bounds])
        w /= w.sum()
        return {a: float(w[i]) for i, a in enumerate(assets)}
    else:
        return {a: float(lo[i] + (1.0 - lo.sum()) / n) for i, a in enumerate(assets)}


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def portfolio_stats(weights: dict[str, float], returns_df: pd.DataFrame, assets: list[str]) -> dict:
    ret = returns_df[assets].dropna()
    w = np.array([weights.get(a, 0.0) for a in assets])
    port_ret = ret.values @ w
    ann_ret = (1 + port_ret.mean()) ** 12 - 1
    ann_vol = port_ret.std() * np.sqrt(12)
    sharpe  = (ann_ret - 0.0) / ann_vol if ann_vol > 0 else 0.0
    max_dd  = _max_drawdown(port_ret)
    return {"CAGR": ann_ret, "Vol": ann_vol, "Sharpe": sharpe, "MaxDD": max_dd, "N": len(port_ret)}


def _max_drawdown(monthly_returns: np.ndarray) -> float:
    nav = np.cumprod(1 + monthly_returns)
    peak = np.maximum.accumulate(nav)
    dd = (nav - peak) / peak
    return float(dd.min())


def print_regime_table(regime_portfolios: dict[str, dict[str, float]],
                       regime_stats: dict[str, dict],
                       assets: list[str], n: int) -> None:
    print(f"\n  {'═' * 68}")
    print(f"  PORTAFOGLI PER REGIME — MacroScore MA({n})")
    print(f"  {'═' * 68}")

    header = f"  {'Regime':<14s}" + "".join(f"{a:>13s}" for a in assets)
    print(header)
    print(f"  {'-' * 66}")

    for regime in REGIMES_ORDER:
        if regime not in regime_portfolios:
            print(f"  {regime:<14s}  (nessun mese nel training period)")
            continue
        w = regime_portfolios[regime]
        weights_str = "".join(f"{w.get(a, 0)*100:12.1f}%" for a in assets)
        print(f"  {regime:<14s}{weights_str}")
        # Mostra i vincoli [min, max] applicati
        b = REGIME_BOUNDS.get(regime, DEFAULT_BOUNDS)
        bounds_str = "".join(
            f"  [{b.get(a, DEFAULT_BOUNDS.get(a, (0,1)))[0]*100:.0f}–{b.get(a, DEFAULT_BOUNDS.get(a, (0,1)))[1]*100:.0f}%]"
            for a in assets
        )
        print(f"  {'':14s}{bounds_str}")

    print(f"\n  {'Regime':<14s}  {'N mesi':>7s}  {'CAGR':>7s}  {'Sharpe':>7s}  {'MaxDD':>8s}")
    print(f"  {'-' * 52}")
    for regime in REGIMES_ORDER:
        if regime not in regime_stats:
            continue
        s = regime_stats[regime]
        print(f"  {regime:<14s}  {s['N']:>7d}  {s['CAGR']:>6.1%}  {s['Sharpe']:>7.2f}  {s['MaxDD']:>7.1%}")


def print_regime_distribution(regime_series: pd.Series, n: int) -> None:
    counts = regime_series.value_counts()
    total  = len(regime_series)
    print(f"\n  Distribuzione regimi con MA({n}):")
    for regime in REGIMES_ORDER:
        cnt = counts.get(regime, 0)
        bar = "█" * int(cnt / total * 30)
        print(f"    {regime:<14s}  {cnt:3d} mesi ({cnt/total:4.0%})  {bar}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=str(TRAINING_START))
    parser.add_argument("--end",   default=str(TRAINING_END))
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end   = date.fromisoformat(args.end)

    print(f"\n{'=' * 70}")
    print(f"  CALIBRAZIONE PORTAFOGLI PER REGIME — training {start} → {end}")
    print(f"{'=' * 70}")

    db = SessionLocal()
    try:
        score_weights = get_macro_score_weights(db)
        thresholds    = get_regime_thresholds(db)
        macro_raw     = load_macro_score_series(db, start, end, score_weights)
        returns_df    = load_returns_df(db, start, end)

        if macro_raw.empty or returns_df.empty:
            print("  ERROR: dati insufficienti per il periodo selezionato")
            return

        assets = [a for a in ["Equity", "Bond", "Commodities", "Cash"] if a in returns_df.columns]

        print(f"\n  MacroScore  : {len(macro_raw)} mesi  ({macro_raw.index.min().date()} → {macro_raw.index.max().date()})")
        print(f"  Returns     : {len(returns_df)} mesi  ({returns_df.index.min().date()} → {returns_df.index.max().date()})")
        print(f"  Assets      : {', '.join(assets)}")
        print(f"  Regimi DB   : {[name for _, name in thresholds]}")
        print(f"  Soglie      : {[(t, n) for t, n in thresholds if t is not None]}")

        results = {}

        for n_ma in [2, 3, 4]:
            macro_smooth  = macro_raw.rolling(n_ma, min_periods=n_ma).mean().dropna()
            regime_series = assign_regimes(macro_smooth, thresholds)

            # Allinea returns al regime: regime[t] → return[t+1] (no look-ahead)
            aligned = pd.concat([regime_series.rename("regime"), returns_df], axis=1).dropna()

            regime_portfolios = {}
            regime_stats      = {}

            for regime in REGIMES_ORDER:
                mask = aligned["regime"] == regime
                regime_returns = aligned.loc[mask, assets]
                if len(regime_returns) < 3:
                    continue
                # Ottimizza su regime[t] → return[t] (stessi mesi del regime)
                # In produzione il portafoglio viene applicato al mese SUCCESSIVO
                portfolio = max_sharpe_portfolio(regime_returns, assets, regime=regime)
                stats     = portfolio_stats(portfolio, regime_returns, assets)
                regime_portfolios[regime] = portfolio
                regime_stats[regime]      = stats

            results[n_ma] = (regime_portfolios, regime_stats, regime_series)
            print_regime_distribution(regime_series, n_ma)
            print_regime_table(regime_portfolios, regime_stats, assets, n_ma)

        # Confronto Sharpe tra N
        print(f"\n  {'═' * 50}")
        print(f"  CONFRONTO SHARPE IN-SAMPLE PER N")
        print(f"  {'═' * 50}")
        print(f"  {'Regime':<14s}" + "".join(f"  MA({n})" for n in [2, 3, 4]))
        print(f"  {'-' * 48}")
        for regime in REGIMES_ORDER:
            row = f"  {regime:<14s}"
            for n_ma in [2, 3, 4]:
                portfolios, stats, _ = results[n_ma]
                if regime in stats:
                    row += f"  {stats[regime]['Sharpe']:>5.2f} "
                else:
                    row += "    —   "
            print(row)

        print(f"\n  Nota: questi Sharpe sono IN-SAMPLE (training period).")
        print(f"  Scegliere N in base alla distribuzione dei regimi e alla plausibilità")
        print(f"  economica dei portafogli, non solo al Sharpe più alto.")
        print()

    finally:
        db.close()


if __name__ == "__main__":
    main()
