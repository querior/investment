import datetime
import json
import math
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import Any, cast
import pandas as pd
import logging
from app.backtest.domain.strategy.strategy_builder import create_bull_put_spread, should_close_position
from app.backtest.schemas.backtest_portfolio_performance import BacktestPortfolioPerformance
from app.backtest.schemas.backtest_position import BacktestPosition
from app.backtest.schemas.backtest_position_snapshot import BacktestPositionSnapshot
from app.db.session import SessionLocal
from app.backtest.schemas import BacktestRun, BacktestWeight, BacktestPerformance
from app.backtest.schemas.backtest_run import BacktestFrequency, BacktestStatus
from app.backtest.schemas.backtest_run_parameter import BacktestRunParameter
from app.backtest.loaders import load_asset_returns
from app.db.market_price import MarketPrice
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
from app.backtest.metrics import compute_metrics, compute_run_eod_metrics
from .domain.models import Portfolio
from app.signals.volatility import enrich_with_iv
from app.backtest.domain.strategy.selectors import select_strategy
from app.services.pillars.service import compute_macro_risk_score

logger = logging.getLogger(__name__)

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
    metrics = compute_metrics(nav_series) # type: ignore[assignment]
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


def execute_eom_backtest(db: Session, run: BacktestRun) -> None:
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
    clean_eom_backtest_run(db, run.id)
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
                new_target = compute_target_allocation(db, regimes, backtest_id=run.backtest_id, coherence_factor=coherence_factor)

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
                db, d, target, run_id=run_id, allocation_alpha=allocation_alpha, backtest_id=run.backtest_id
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
                period_return=ret,
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
    
def clean_eom_backtest_run(db: Session, run_id: int):
    run = (
        db.query(BacktestRun)
        .options(joinedload(BacktestRun.backtest))
        .filter(BacktestRun.id == run_id)
        .first()
    )
    
    
    db.query(BacktestPerformance).filter(BacktestPerformance.run_id == run_id).delete()
    db.query(BacktestWeight).filter(BacktestWeight.run_id == run_id).delete()
    db.query(AllocationHistory).filter(AllocationHistory.run_id == run_id).delete()

    for field in ("cagr", "volatility", "sharpe", "max_drawdown", "win_rate", "profit_factor", "n_trades", "config_snapshot", "error_message"):
        setattr(run, field, None)
    setattr(run, "status", BacktestStatus.READY)
    db.commit()
    
def cleanup_eod_backtest_run(db: Session, run_id: int) -> None:
    run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()    
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run.cagr = None
    run.sharpe = None
    run.volatility = None
    run.max_drawdown = None
    run.win_rate = None
    run.profit_factor = None
    run.n_trades = None
    
    db.query(BacktestPerformance).filter(BacktestPerformance.run_id == run_id).delete()
    db.query(BacktestPositionSnapshot).filter(
        BacktestPositionSnapshot.run_id == run_id
    ).delete()
    
    db.query(BacktestPosition).filter(
        BacktestPosition.run_id == run_id
    ).delete()
    
    db.query(BacktestPortfolioPerformance).filter(
        BacktestPortfolioPerformance.run_id == run_id
    ).delete()
    
    db.commit()

def run_eod_backtest(
    db: Session,
    run: BacktestRun,
    df: pd.DataFrame,
    initial_cash: float = 3000,
    entry_every_n_days: int = 30
) -> None:
    cleanup_eod_backtest_run(db,run.id)
    
    logger.warning(f"Start backtest execution -> {df.tail()}")
    try:
        portfolio = Portfolio(initial_cash=initial_cash)
        position_ids: dict[int,int] = {}
        
        nav_series: list[float] = []
        return_series: list[float] = []
        prev_nav: float | None = None
        total_trades = 0

        for i, (_, row) in enumerate(df.iterrows()):
            date = pd.to_datetime(row["date"]).date().isoformat()
            S = float(row["close"])
            iv = float(row["iv"])
            
            new_positions_count = 0
            closed_positions_count = 0
            
            # 1. update market sulle posizioni aperte
            for position in portfolio.positions:
                if position.is_open:
                    position.update_market(S=S, sigma=iv, dt_years=1 / 365.0)
                    
            # 2. salva snapshot posizione PRIMA della chiusura
            for position in portfolio.positions:
                if not position.is_open:
                    continue
                
                db_position_id = position_ids.get(id(position))
                if db_position_id is None:
                    continue
                
                pos_snapshot = BacktestPositionSnapshot(
                    run_id=run.id,
                    position_id=db_position_id,
                    snapshot_date=date,
                    underlying_price=S,
                    iv=iv,
                    position_price=position.price,
                    position_pnl=position.pnl,
                    position_delta=position.delta,
                    position_gamma=position.gamma,
                    position_theta=position.theta,
                    position_vega=position.vega,
                    min_dte=min(leg.state.T for leg in position.legs),
                    is_open=position.is_open,
                )
                db.add(pos_snapshot)

            # 3. close logic
            for position in portfolio.positions:
                if position.is_open and should_close_position(position):
                    logger.warning(f"close position: {position.name} {position.opened_at}")
                    portfolio.close_position(position)
                    closed_positions_count += 1
                    
                db_position_id = position_ids.get(id(position))
                if db_position_id is not None:
                    db_position = db.get(BacktestPosition,db_position_id)
                    if db_position:
                        db_position.status = "CLOSED"
                        db_position.closed_at = date
                        db_position.close_value = position.price
                        db_position.realized_pnl = position.pnl

            portfolio.remove_closed_positions()

            # 4. entry logic
            if i % entry_every_n_days == 0:
                macro_score, macro_regime = compute_macro_risk_score(db, pd.to_datetime(row["date"]).date())
                
                strategy = select_strategy(iv, macro_regime)
                
                logger.warning(f"Strategy: {strategy.name} - macro_score: {macro_score} macro_regime: {macro_regime} ")
                
                if strategy.should_trade:                
                    new_position = strategy.builder(
                        date=date,
                        S=S,
                        iv=iv,
                        dte_days=45,
                        quantity=1,
                    )
                    logger.warning(f"open position: {new_position.name} {new_position.opened_at} - macro_score: {macro_score} macro_regime: {macro_regime} ")
                    portfolio.open_position(new_position)
                    new_positions_count += 1
                    
                    # Converti position_type in snake_case per FK a option_strategies
                    position_type_key = new_position.name.lower().replace(" ", "_")

                    db_position = BacktestPosition(
                        run_id=run.id,
                        position_type=position_type_key,
                        status="OPEN",
                        opened_at=date,
                        entry_underlying=S,
                        entry_iv=iv,
                        entry_macro_regime=None,
                        initial_value=new_position.initial_value,
                    )
                    db.add(db_position)
                    db.flush() # serve per ottenere db_position.id
                    
                    position_ids[id(new_position)] = db_position.id
                    total_trades += 1

            # # 5. salva performance portfolio
            positions_value = portfolio.positions_value()
            total_equity = portfolio.total_equity
            
            perf = BacktestPortfolioPerformance(
                run_id=run.id,
                snapshot_date=date,
                cash=portfolio.cash,
                positions_value=positions_value,
                total_equity=total_equity,
                realized_pnl=portfolio.realized_pnl,
                unrealized_pnl=portfolio.unrealized_pnl,
                total_pnl=portfolio.total_pnl,
                total_delta=portfolio.total_delta,
                total_gamma=portfolio.total_gamma,
                total_theta=portfolio.total_theta,
                total_vega=portfolio.total_vega,
                open_positions_count=len([p for p in portfolio.positions if p.is_open]),
                closed_positions_count=closed_positions_count,
                new_positions_count=new_positions_count,
                underlying_price=S,
                iv=iv,
            )
            db.add(perf)
            
            period_return = 0.0 if prev_nav in (None, 0) else (total_equity / prev_nav) - 1.0

            perf_summary = BacktestPerformance(
                run_id=run.id,
                date=date,
                nav=total_equity,
                period_return=period_return,  
            )
            db.add(perf_summary)

            nav_series.append(total_equity)
            return_series.append(period_return)
            prev_nav = total_equity

        # successo
        metrics = compute_run_eod_metrics(nav_series, return_series)
        
        run.cagr = metrics["cagr"]
        run.volatility = metrics["volatility"]
        run.sharpe = metrics["sharpe"]
        run.max_drawdown = metrics["max_drawdown"]
        run.win_rate = metrics["win_rate"]
        run.profit_factor = metrics["profit_factor"]
        run.n_trades = total_trades
        run.error_message = None
        db.commit()
    except Exception as e:
        db.rollback()
        run.error_message = str(e)
        db.commit()
        raise
        


def execute_eod_backtest(db: Session, run: BacktestRun) -> None:
    params = db.query(BacktestRunParameter).filter(BacktestRunParameter.run_id == run.id).all()
    if not params:
        run.error_message = "Undefined params for backtest"
        db.commit()
        raise HTTPException(status_code=404, detail="Undefined params for backtest")
    params_dict = {
        p.key: {
            "value": p.value,
            "unit": p.unit,
        }
        for p in params
    }
    
    symbol = params_dict.get("symbol")
    symbol_str = symbol.get("value") if isinstance(symbol, dict) else symbol

    if not symbol_str or not params_dict.get("initial_capital"):
        run.error_message = "Undefined params initial_capital for backtest"
        db.commit()
        raise HTTPException(status_code=400, detail="Undefined params initial_capital for backtest")
    
    warmup_days = 40
    load_start = run.start_date - datetime.timedelta(days=warmup_days) # type: ignore
    load_end = run.end_date

    data = db.query(MarketPrice).filter(
               MarketPrice.symbol == symbol_str,
               MarketPrice.date >= load_start,
               MarketPrice.date <= load_end
            ).all()
    rows = [
        {
            "symbol": x.symbol,
            "date": x.date,
            "close": x.close,
        }
        for x in data
    ]
    df = pd.DataFrame(rows, columns=["symbol", "date","close"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.reset_index(drop=True)
    # uso funzione proxy - in futuro da cambiare con surface
    alpha_volatility = params_dict.get("alpha_volatility")
    iv_min = params_dict.get("iv_min")
    iv_max = params_dict.get("iv_max")    
    
    df = enrich_with_iv(
        df,
        alpha=float(alpha_volatility["value"]) if alpha_volatility else 4.0,
        iv_min=float(iv_min["value"]) if iv_min else 0.10,
        iv_max=float(iv_max["value"]) if iv_max else 0.80,
    )
    
    df = df[(df["date"] >= pd.Timestamp(run.start_date)) & (df["date"] <= pd.Timestamp(run.end_date))] # type: ignore
    
    logger.warning(f"anteprima -> {df.head()}")
    initial_capital = params_dict.get("initial_capital")
    initial_capital = float(initial_capital["value"]) if initial_capital else 0.0
    days = params_dict.get("entry_every_n_days")
    entry_every_n_days = int(days["value"]) if days is not None else 30
    run_eod_backtest(db, run, df, initial_cash=initial_capital, entry_every_n_days=entry_every_n_days)


def run_in_background(run_id: int) -> None:
    logger.warning(f"run_in_background {run_id}")
    """Entry point per il thread background. Crea la propria sessione DB."""
    db = SessionLocal()
    try:
        run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()
        
        if not run:
            raise HTTPException(status_code=404, detail="Backtest not fount")
        
        if run.frequency == BacktestFrequency.EOM:
            execute_eom_backtest(db, run)
        elif run.frequency == BacktestFrequency.EOD:
            execute_eod_backtest(db, run)
        else:
            raise HTTPException(status_code=400, detail="Backtest not yet implemented") 
    except Exception as e:
        print(f"[RUN {run_id}] Background error: {e}")
    finally:
        db.close()
        
