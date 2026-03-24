import json
from sqlalchemy.orm import Session
from typing import Any, cast
from app.backtest.schemas import BacktestRun, BacktestWeight, BacktestPerformance
from app.backtest.schemas.backtest_run import BacktestStatus
from app.backtest.loaders import load_asset_returns
from app.services.allocation.engine import compute_allocation
from app.services.config_repo import get_macro_score_weights, get_sensitivity, get_neutral_allocation, get_allocation_parameter
from app.db.macro_pillar import MacroPillar
from app.backtest.metrics import compute_metrics


def _update_metrics(db: Session, run: BacktestRun, n_trades: int) -> None:
    """Ricalcola e salva le metriche sui dati parziali o completi già scritti."""
    nav_series = [
        r.nav for r in (
            db.query(BacktestPerformance)
            .filter(BacktestPerformance.run_id == run.id)
            .order_by(BacktestPerformance.date)
            .all()
        )
    ]
    metrics = compute_metrics(nav_series)
    r: Any = run
    if metrics:
        r.cagr = metrics["cagr"]
        r.volatility = metrics["volatility"]
        r.sharpe = metrics["sharpe"]
        r.max_drawdown = metrics["max_drawdown"]
        r.win_rate = metrics["win_rate"]
        r.profit_factor = metrics.get("profit_factor")
    r.n_trades = n_trades


def execute_backtest(db: Session, run: BacktestRun) -> None:
    """
    Esegue il backtest sul run passato.

    Vincoli:
    - No look-ahead: per ogni data d si usano solo pillar disponibili a d o precedente.
    - Skip recompute: se il dato dei pillar non è cambiato rispetto al ciclo precedente,
      si riutilizzano i pesi precedenti senza ricalcolare (NAV aggiornato comunque).
    - Commit per ciclo: ogni riga è immediatamente visibile.
    """
    r: Any = run
    # Snapshot della configurazione usata per questa esecuzione
    r.config_snapshot = json.dumps({
        "sensitivity": get_sensitivity(db),
        "neutral": get_neutral_allocation(db),
        "scale_k": get_allocation_parameter(db, "scale_factor_k", 0.05),
        "max_abs_delta": get_allocation_parameter(db, "max_abs_delta", 0.10),
        "macro_score_weights": get_macro_score_weights(db),
    })
    # Pulizia dati precedenti (idempotente: permette ri-esecuzione)
    db.query(BacktestWeight).filter(BacktestWeight.run_id == run.id).delete()
    db.query(BacktestPerformance).filter(BacktestPerformance.run_id == run.id).delete()
    r.cagr = None
    r.volatility = None
    r.sharpe = None
    r.max_drawdown = None
    r.win_rate = None
    r.profit_factor = None
    r.n_trades = None
    r.error_message = None
    r.status = BacktestStatus.RUNNING
    r.stop_requested = False
    db.commit()

    try:
        returns = load_asset_returns(db, run.start_date, run.end_date, frequency=run.frequency.value)
        score_weights = get_macro_score_weights(db)
        nav = 1.0
        dates = sorted(returns.keys())

        last_pillar_date = None
        last_weights: dict = {}
        n_trades = 0

        for i in range(len(dates) - 1):
            # --- controlla segnale di stop ---
            db.refresh(run)
            if r.stop_requested:
                _update_metrics(db, run, n_trades)
                r.status = BacktestStatus.STOPPED
                db.commit()
                return

            d = dates[i]
            next_d = dates[i + 1]

            # --- no look-ahead: pillar più recente disponibile <= d ---
            latest_date_row = (
                db.query(MacroPillar.date)
                .filter(MacroPillar.date <= d)
                .order_by(MacroPillar.date.desc())
                .first()
            )
            if not latest_date_row:
                continue

            current_pillar_date = latest_date_row[0]

            # --- skip recompute se MacroScore non aggiornato ---
            if current_pillar_date == last_pillar_date and last_weights:
                weights = last_weights
                macro_score = None
                pillars = {}
            else:
                pillars_rows = (
                    db.query(MacroPillar)
                    .filter(MacroPillar.date == current_pillar_date)
                    .all()
                )
                if not pillars_rows:
                    continue

                pillars = {r.pillar: r.score for r in pillars_rows}
                macro_score = sum(score_weights.get(p, 0.0) * s for p, s in pillars.items())
                new_weights = compute_allocation(db, pillars)

                if new_weights != last_weights:
                    n_trades += 1

                weights = new_weights
                last_weights = weights
                last_pillar_date = current_pillar_date

                pillar_str = "  ".join(f"{p}={s:+.2f}" for p, s in sorted(pillars.items()))
                weights_str = "  ".join(f"{a}={w:.1%}" for a, w in sorted(weights.items()))
                print(f"  {d}  MacroScore={macro_score:+.3f}  [{pillar_str}]  →  {weights_str}")

            if not weights:
                continue

            # --- scrivi allocazione ---
            pillar_scores_json = json.dumps({p: round(s, 4) for p, s in pillars.items()}) if pillars else None
            for asset, w in weights.items():
                db.add(BacktestWeight(
                    run_id=run.id,
                    date=next_d,
                    asset=asset,
                    weight=w,
                    macro_score=macro_score,
                    pillar_scores=pillar_scores_json,
                ))

            ret = sum(
                weights.get(asset, 0.0) * returns[next_d].get(asset, 0.0)
                for asset in weights
            )
            nav *= (1 + ret)

            db.add(BacktestPerformance(
                run_id=run.id,
                date=next_d,
                nav=nav,
                monthly_return=ret,
            ))

            # commit per ciclo + aggiorna metriche parziali
            db.commit()
            _update_metrics(db, run, n_trades)
            db.commit()

        r.status = BacktestStatus.DONE
        db.commit()

        cagr = f"{run.cagr:.2%}" if run.cagr is not None else "n/a"
        vol  = f"{run.volatility:.2%}" if run.volatility is not None else "n/a"
        sh   = f"{run.sharpe:.2f}" if run.sharpe is not None else "n/a"
        dd   = f"{run.max_drawdown:.2%}" if run.max_drawdown is not None else "n/a"
        print(f"[RUN {run.id}] DONE  CAGR={cagr} | Vol={vol} | Sharpe={sh} | MaxDD={dd} | Trades={n_trades}")

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
