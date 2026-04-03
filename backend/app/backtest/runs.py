import datetime
import json
import math
from sqlalchemy.orm import Session
from typing import Any, cast
from app.backtest.schemas import BacktestRun, BacktestWeight, BacktestPerformance
from app.backtest.schemas.backtest_run import BacktestStatus
from app.backtest.schemas.backtest_run_parameter import BacktestRunParameter
from app.backtest.loaders import load_asset_returns
from app.services.allocation.engine import (
    compute_target_allocation,
    compute_effective_allocation,
    save_allocation,
)
from app.db.asset_class import AssetClass
from app.services.config_repo import get_neutral_allocation, get_allocation_parameter
from app.db.allocation_adjustment import AllocationAdjustment
from app.db.allocation_history import AllocationHistory
from app.db.macro_regimes import MacroRegime
from app.backtest.metrics import compute_metrics


def _update_metrics(db: Session, run: BacktestRun, n_trades: int) -> None:
    """Ricalcola e salva le metriche sui dati parziali o completi già scritti."""
    nav_series: list[float] = [
        r.nav  # type: ignore[list-item]
        for r in (
            db.query(BacktestPerformance)
            .filter(BacktestPerformance.run_id == run.id)
            .order_by(BacktestPerformance.date)
            .all()
        )
    ]
    metrics = compute_metrics(nav_series)
    r: Any = run
    if metrics:
        def _safe(v: float | None) -> float | None:
            return None if v is None or not math.isfinite(v) else v
        r.cagr         = _safe(metrics["cagr"])
        r.volatility   = _safe(metrics["volatility"])
        r.sharpe       = _safe(metrics["sharpe"])
        r.max_drawdown = _safe(metrics["max_drawdown"])
        r.win_rate     = _safe(metrics["win_rate"])
        r.profit_factor = _safe(metrics.get("profit_factor"))
    r.n_trades = n_trades


def execute_backtest(db: Session, run: BacktestRun) -> None:
    """
    Esegue il backtest sul run passato seguendo il flusso mensile di layer-long:
      regime detection → compute_target_allocation → compute_effective_allocation → save_allocation

    Vincoli:
    - No look-ahead: per ogni data d si usano solo regimi disponibili a d o precedente.
    - Skip recompute target: se il regime date non è cambiato si riusa il target precedente,
      ma compute_effective_allocation viene comunque chiamata ogni mese.
    - Commit per ciclo: ogni riga è immediatamente visibile.
    """
    r: Any = run
    run_id = cast(int, run.id)

    # --- leggi parametri per-run ---
    param_rows = db.query(BacktestRunParameter).filter(BacktestRunParameter.run_id == run_id).all()
    params = {p.key: p.value for p in param_rows}
    coherence_factor    = float(params.get("coherence.factor",  str(get_allocation_parameter(db, "coherence.factor", run.backtest_id, 0.5))))
    allocation_alpha    = float(params.get("allocation.alpha",  str(get_allocation_parameter(db, "allocation.alpha", run.backtest_id, 0.3))))
    initial_allocation  = params.get("initial_allocation", "neutral")

    # --- snapshot configurazione al momento dell'esecuzione ---
    adjustments = db.query(AllocationAdjustment).all()
    r.config_snapshot = json.dumps({
        "neutral":           get_neutral_allocation(db),
        "coherence_factor":  coherence_factor,
        "allocation_alpha":  allocation_alpha,
        "initial_allocation": initial_allocation,
        "adjustments": [
            {"pillar": a.pillar, "regime": a.regime, "asset": a.asset, "delta": a.delta}
            for a in adjustments
        ],
    })

    # --- pulizia dati precedenti (idempotente) ---
    db.query(BacktestWeight).filter(BacktestWeight.run_id == run_id).delete()
    db.query(BacktestPerformance).filter(BacktestPerformance.run_id == run_id).delete()
    db.query(AllocationHistory).filter(AllocationHistory.run_id == run_id).delete()
    for field in ("cagr", "volatility", "sharpe", "max_drawdown", "win_rate", "profit_factor", "n_trades", "error_message"):
        setattr(r, field, None)
    r.status = BacktestStatus.RUNNING
    r.stop_requested = False
    db.commit()

    try:
        returns = load_asset_returns(db, cast(datetime.date, run.start_date), cast(datetime.date, run.end_date), frequency=run.frequency.value)
        dates   = sorted(returns.keys())
        nav     = 1.0
        n_trades = 0

        last_regime_date = None
        last_target: dict = {}
        last_regimes: dict = {}

        # --- seed AllocationHistory se initial_allocation == "neutral" ---
        # Inserisce il portafoglio neutro (range 0-1) come effective del mese precedente
        # al primo ciclo, così compute_effective_allocation parte da lì.
        if initial_allocation == "neutral" and dates:
            acs       = db.query(AssetClass).order_by(AssetClass.display_order).all()
            raw_n     = {a.name: a.neutral_weight for a in acs}
            total_n   = sum(raw_n.values()) or 1.0
            neutral_scaled = {k: v / total_n for k, v in raw_n.items()}
            first_d   = dates[0]
            seed_date = (first_d.replace(day=1) - datetime.timedelta(days=1)).replace(day=1)
            save_allocation(db, seed_date, neutral_scaled, neutral_scaled, run_id=run_id)

        for i in range(len(dates) - 1):
            # --- controlla segnale di stop ---
            db.refresh(run)
            if r.stop_requested:
                _update_metrics(db, run, n_trades)
                r.status = BacktestStatus.STOPPED
                db.commit()
                return

            d      = dates[i]
            next_d = dates[i + 1]

            # --- no look-ahead: regime più recente disponibile <= d ---
            latest_date_row = (
                db.query(MacroRegime.date)
                .filter(MacroRegime.date <= d)
                .order_by(MacroRegime.date.desc())
                .first()
            )
            if not latest_date_row:
                continue

            current_regime_date = latest_date_row[0]

            # --- skip recompute target se regime invariato ---
            if current_regime_date == last_regime_date and last_target:
                target  = last_target
                regimes = last_regimes
            else:
                regime_rows = (
                    db.query(MacroRegime)
                    .filter(MacroRegime.date == current_regime_date)
                    .all()
                )
                if not regime_rows:
                    continue

                regimes    = {row.pillar: row.regime for row in regime_rows}
                new_target = compute_target_allocation(db, regimes, run.backtest_id, coherence_factor=coherence_factor)

                if new_target != last_target:
                    n_trades += 1

                target           = new_target
                last_target      = target
                last_regimes     = regimes
                last_regime_date = current_regime_date

            if not target:
                continue

            # --- compute_effective_allocation (EWM via AllocationHistory scoped per run) ---
            effective = compute_effective_allocation(
                db, d, target, run.backtest_id, run_id=run_id, allocation_alpha=allocation_alpha,
            )

            # --- persiste in AllocationHistory per il ciclo successivo ---
            save_allocation(db, d, target, effective, run_id=run_id)

            # --- scrivi pesi effettivi nel backtest ---
            pillar_regimes_json = json.dumps(regimes)
            for asset, w in effective.items():
                db.add(BacktestWeight(
                    run_id=run_id,
                    date=next_d,
                    asset=asset,
                    weight=w,
                    pillar_scores=pillar_regimes_json,
                ))

            ret = sum(
                effective.get(asset, 0.0) * returns[next_d].get(asset, 0.0)
                for asset in effective
            )
            nav *= (1 + ret)

            db.add(BacktestPerformance(
                run_id=run_id,
                date=next_d,
                nav=nav,
                monthly_return=ret,
            ))

            db.commit()
            _update_metrics(db, run, n_trades)
            db.commit()

        r.status = BacktestStatus.DONE
        db.commit()

        cagr = f"{run.cagr:.2%}" if run.cagr is not None else "n/a"
        vol  = f"{run.volatility:.2%}" if run.volatility is not None else "n/a"
        sh   = f"{run.sharpe:.2f}" if run.sharpe is not None else "n/a"
        dd   = f"{run.max_drawdown:.2%}" if run.max_drawdown is not None else "n/a"
        print(f"[RUN {run_id}] DONE  CAGR={cagr} | Vol={vol} | Sharpe={sh} | MaxDD={dd} | Trades={n_trades}")

    except Exception as e:
        r.status = BacktestStatus.ERROR
        r.error_message = str(e)
        db.commit()
        raise e


def run_in_background(run_id: int) -> None:
    """Entry point per il thread background. Crea la propria sessione DB."""
    from app.db.session import SessionLocal
    db = SessionLocal()
    try:
        run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
        if run:
            execute_backtest(db, run)
    except Exception as e:
        print(f"[RUN {run_id}] Background error: {e}")
    finally:
        db.close()
