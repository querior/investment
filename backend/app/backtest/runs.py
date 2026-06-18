import datetime
import json
import math
import traceback
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import Any, cast
import pandas as pd
import logging
from app.backtest.domain.agents.exit_agent import ExitAgent
from app.backtest.schemas.backtest_portfolio_performance import BacktestPortfolioPerformance
from app.backtest.schemas.backtest_position import BacktestPosition
from app.backtest.schemas.backtest_position_snapshot import BacktestPositionSnapshot
from app.db.session import SessionLocal
from app.backtest.schemas import BacktestRun, BacktestWeight, BacktestPerformance
from app.backtest.schemas.backtest_run import BacktestFrequency, BacktestStatus
from app.backtest.schemas.backtest_run_parameter import BacktestRunParameter
from app.backtest.loaders import load_asset_returns
from app.services.allocation.engine import (
    compute_target_allocation,
    compute_effective_allocation,
    save_allocation,
)
from app.db.asset_class import AssetClass
from app.services.config_repo import get_neutral_allocation, get_allocation_parameter, get_instrument_config
from app.db.allocation_adjustment import AllocationAdjustment
from app.db.allocation_history import AllocationHistory
from app.db.macro_regimes import MacroRegime
from app.db.decision_log import DecisionLog
from app.backtest.metrics import compute_metrics, compute_run_eod_metrics
from .domain.models import Portfolio
from app.backtest.data_preparation.base import prepare_market_df
from app.backtest.data_preparation.pipeline import build_backtest_dataset
from app.backtest.domain.option.ev import compute_trade_ev
from app.engines.option import DecisionEngine
from app.engines.option.strategy_selector import STRATEGY_BY_NAME

logger = logging.getLogger(__name__)


def _float_or_none(v) -> float | None:
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except (TypeError, ValueError):
        return None


def _scale_position(position, multiplier: float) -> None:
    """
    Scale position size by multiplier (quality-based sizing).

    Args:
        position: Position object with legs
        multiplier: Size multiplier (0.0-1.0)
    """
    for leg in position.legs:
        leg.quantity = int(leg.quantity * multiplier)
        if leg.quantity < 1:
            leg.quantity = 1  # Minimum 1 contract


def _build_exit_config(params_dict: dict) -> dict:
    """
    Costruisce il config delle exit rules dai BacktestRunParameter.
    Convenzione chiavi: exit.<regola>.<campo>
    Se un parametro non è presente si applica il default della regola.
    """
    def _get(key: str, default: str) -> str:
        p = params_dict.get(key)
        return p["value"] if p else default

    def _bool(key: str, default: bool) -> bool:
        return _get(key, str(default).lower()).lower() == "true"

    return {
        "rule_dte": {
            "enabled": _bool("exit.rule_dte.enabled", True),
            "threshold_days": float(_get("exit.rule_dte.threshold_days", "21")),
        },
        "rule_profit_target": {
            "enabled": _bool("exit.rule_profit_target.enabled", True),
            "threshold_pct": float(_get("exit.rule_profit_target.threshold_pct", "50")),
        },
        "rule_stop_loss": {
            "enabled": _bool("exit.rule_stop_loss.enabled", True),
            "threshold_pct": float(_get("exit.rule_stop_loss.threshold_pct", "200")),
        },
        "rule_trailing_stop": {
            "enabled": _bool("exit.rule_trailing_stop.enabled", False),
            "min_profit_pct": float(_get("exit.rule_trailing_stop.min_profit_pct", "30")),
            "pullback_pct": float(_get("exit.rule_trailing_stop.pullback_pct", "15")),
        },
        "rule_macro_reversal": {
            "enabled": _bool("exit.rule_macro_reversal.enabled", True),
        },
        "rule_momentum_reversal": {
            "enabled": _bool("exit.rule_momentum_reversal.enabled", True),
            "rsi_threshold": float(_get("exit.rule_momentum_reversal.rsi_threshold", "30")),
            "use_macd": _bool("exit.rule_momentum_reversal.use_macd", True),
        },
        "rule_iv_spike": {
            "enabled": _bool("exit.rule_iv_spike.enabled", False),
            "threshold_ratio": float(_get("exit.rule_iv_spike.threshold_ratio", "2.0")),
        },
        "rule_delta_breach": {
            "enabled": _bool("exit.rule_delta_breach.enabled", False),
            "threshold": float(_get("exit.rule_delta_breach.threshold", "0.50")),
        },
        "rule_theta_decay": {
            "enabled": _bool("exit.rule_theta_decay.enabled", False),
            "threshold_ratio": float(_get("exit.rule_theta_decay.threshold_ratio", "0.05")),
        },
        "portfolio_trailing_stop": {
            "enabled": _bool("exit.portfolio_trailing_stop.enabled", False),
            "pullback_pct": float(_get("exit.portfolio_trailing_stop.pullback_pct", "20")),
        },
    }

def _build_entry_config(params_dict: dict) -> dict:
    """
    Costruisce il config dei filtri di entry dai BacktestRunParameter.
    Convenzione chiavi: entry.<campo> e entry_score.<campo>
    """
    def _get(key: str, default: str) -> str:
        p = params_dict.get(key)
        return p["value"] if p else default

    return {
        # Legacy filters
        "iv_min_threshold": float(_get("entry.iv_min_threshold", "0.18")),
        "rsi_min_bull": float(_get("entry.rsi_min_bull", "40")),
        "iv_min_neutral": float(_get("entry.iv_min_neutral", "0.15")),
        "iv_rv_ratio_min": float(_get("entry.iv_rv_ratio_min", "1.1")),

        # Entry Score Components (weights, must sum to 1.0)
        "entry_score.w1_iv_rank": float(_get("entry_score.w1_iv_rank", "0.30")),
        "entry_score.w2_iv_hv": float(_get("entry_score.w2_iv_hv", "0.20")),
        "entry_score.w3_squeeze": float(_get("entry_score.w3_squeeze", "0.20")),
        "entry_score.w4_rsi": float(_get("entry_score.w4_rsi", "0.15")),
        "entry_score.w5_dte": float(_get("entry_score.w5_dte", "0.10")),
        "entry_score.w6_volume": float(_get("entry_score.w6_volume", "0.05")),

        # DTE Score parameters
        "entry_score.dte_min": int(_get("entry_score.dte_min", "21")),
        "entry_score.dte_optimal_min": int(_get("entry_score.dte_optimal_min", "35")),
        "entry_score.dte_optimal_max": int(_get("entry_score.dte_optimal_max", "45")),
        "entry_score.dte_max": int(_get("entry_score.dte_max", "55")),

        # RSI Neutrality parameters
        "entry_score.rsi_neutral_min": float(_get("entry_score.rsi_neutral_min", "40")),
        "entry_score.rsi_neutral_max": float(_get("entry_score.rsi_neutral_max", "60")),

        # Sizing thresholds
        "entry_size.threshold_full": float(_get("entry_size.threshold_full", "75")),
        "entry_size.threshold_reduced": float(_get("entry_size.threshold_reduced", "60")),
        "entry_size.multiplier_full": float(_get("entry_size.multiplier_full", "1.0")),
        "entry_size.multiplier_reduced": float(_get("entry_size.multiplier_reduced", "0.75")),
    }


def _build_position_config(params_dict: dict) -> dict:
    """
    Costruisce il config di position sizing dai BacktestRunParameter.
    Usato da DecisionEngine per il calcolo della size dei contratti.

    debug.force_open: se "true", bypassa il threshold L5 e forza OPEN su ogni
    candidato con builder valido. Usare solo per verificare la copertura della
    matrice zona-strategia, non per backtest reali.
    """
    def _get(key: str, default: str) -> str:
        p = params_dict.get(key)
        return p["value"] if p else default

    force_open = _get("debug.force_open", "false").lower() == "true"

    return {
        "size_multiplier": 1.0,
        "available_risk": float(_get("max_risk", "3")) / 100.0,
        "decision_threshold_open": 0.0 if force_open else 75.0,
        "decision_threshold_skip": 0.0 if force_open else 60.0,
        "debug_force_open": force_open,
    }


def _build_risk_config(params_dict: dict) -> dict:
    """
    Costruisce il config di rischio per il Decision Layer (L1-L5).
    Include soglie di decision score e pesi del scoring multidimensionale.
    """
    def _get(key: str, default: str) -> str:
        p = params_dict.get(key)
        return p["value"] if p else default

    return {
        "threshold_open": float(_get("decision.threshold_open", "75")),
        "threshold_monitor": float(_get("decision.threshold_monitor", "60")),
        "max_bid_ask_pct": float(_get("decision.max_bid_ask_pct", "15")) / 100.0,
        "weights": {
            "edge": float(_get("opportunity.weight_edge", "0.35")),
            "risk_reward": float(_get("opportunity.weight_rr", "0.25")),
            "breakeven": float(_get("opportunity.weight_bep", "0.20")),
            "execution": float(_get("opportunity.weight_execution", "0.15")),
            "efficiency": float(_get("opportunity.weight_efficiency", "0.05")),
        },
    }


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

        # Cooldown tracking: {strategy_name: close_date}
        recent_closes = {}

        for i in range(len(dates) - 1):
            # --- controlla segnale di stop ---
            db.refresh(run)
            if run.stop_requested:
                _update_metrics(db, run, n_trades)
                run.status = BacktestStatus.STOPPED
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

        run.status = BacktestStatus.DONE
        db.commit()

        cagr = f"{run.cagr:.2%}" if run.cagr is not None else "n/a"
        vol  = f"{run.volatility:.2%}" if run.volatility is not None else "n/a"
        sh   = f"{run.sharpe:.2f}" if run.sharpe is not None else "n/a"
        dd   = f"{run.max_drawdown:.2%}" if run.max_drawdown is not None else "n/a"
        print(f"[RUN {run_id}] DONE  CAGR={cagr} | Vol={vol} | Sharpe={sh} | MaxDD={dd} | Trades={n_trades}")

    except Exception as e:
        run.status = BacktestStatus.ERROR
        run.error_message = str(e)
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
    run.max_consecutive_losses = None
    
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

    db.query(DecisionLog).filter(DecisionLog.run_id == run_id).delete()

    db.commit()

def run_eod_backtest(
    db: Session,
    run: BacktestRun,
    df: pd.DataFrame,
    initial_cash: float = 3000,
    entry_every_n_days: int = 30,
    instrument=None,
    exit_config: dict | None = None,
    entry_config: dict | None = None,
    position_config: dict | None = None,
    risk_config: dict | None = None,
    strategy_overrides: dict | None = None,
    rollout_config: dict | None = None,
) -> None:
    cleanup_eod_backtest_run(db, run.id)

    logger.warning(f"Start backtest execution -> {df.tail()}")

    # Initialize Decision Engine (L1-L5 pipeline)
    engine = DecisionEngine()
    if position_config is None:
        position_config = {}
    if risk_config is None:
        risk_config = {}

    try:
        portfolio = Portfolio(initial_cash=initial_cash)
        exit_agent = ExitAgent(
            exit_config=exit_config or {},
            strategy_overrides=strategy_overrides,
            rollout_config=rollout_config,
            portfolio_trailing_stop=(exit_config or {}).get("portfolio_trailing_stop", {}),
        )
        position_ids: dict[int,int] = {}

        nav_series: list[float] = []
        return_series: list[float] = []
        trade_pnls: list[float] = []
        prev_nav: float | None = None
        total_trades = 0
        recent_closes: dict[str, str] = {}  # Track strategy close dates for cooldown

        for _, row in df.iterrows():
            date = pd.to_datetime(row["date"]).date().isoformat()
            S = float(row["close"])
            iv = float(row["iv"])
            
            new_positions_count = 0
            closed_positions_count = 0
            pending_rollouts: list[tuple[str, str, int]] = []

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
                db.commit()

            # 3. close logic — ExitAgent decides HOLD / CLOSE / ROLL per position
            exit_agent.update_portfolio_peak(portfolio.total_equity)

            for position in portfolio.positions:
                if not position.is_open:
                    continue

                signal = exit_agent.decide(position=position, row=row, portfolio=portfolio)

                if signal.action == "HOLD":
                    continue

                db_position_id = position_ids.get(id(position))
                db_position = db.get(BacktestPosition, db_position_id) if db_position_id else None

                exit_reason = signal.triggered_by
                logger.warning(f"close position: {position.name} {position.opened_at} - reason: {exit_reason} action: {signal.action}")

                _entry_comm = 0.0
                _exit_comm = 0.0

                if instrument is not None:
                    _entry_comm = (db_position.entry_transaction_costs or 0.0) if db_position else 0.0
                    _n_contracts = sum(leg.quantity for leg in position.legs)
                    _exit_comm = instrument.cost_model.total_cost(abs(position.price), _n_contracts)

                net_pnl = position.pnl - _entry_comm - _exit_comm
                trade_pnls.append(net_pnl)
                portfolio.close_position(position)
                portfolio.apply_commission(_entry_comm + _exit_comm)
                closed_positions_count += 1
                recent_closes[position.name] = date

                if signal.action == "ROLL":
                    _n_roll = position.legs[0].quantity if position.legs else 1
                    pending_rollouts.append((position.name, getattr(position, "entry_zone", ""), _n_roll))
                    logger.warning(f"[ROLLOUT QUEUED {date}] {position.name} zone={getattr(position, 'entry_zone', '')} net_pnl={net_pnl:.2f}")

                if db_position is not None:
                    db_position.status = "CLOSED"
                    db_position.closed_at = date
                    db_position.close_value = position.price
                    db_position.realized_pnl = net_pnl
                    db_position.exit_transaction_costs = _exit_comm if _exit_comm > 0 else None
                    if signal.exit_conditions:
                        db_position.exit_conditions = signal.exit_conditions
                db.commit()

            portfolio.remove_closed_positions()

            # 4. record portfolio NAV/performance — after closes, before new opens
            positions_value = portfolio.positions_value()
            total_equity = portfolio.total_equity

            period_return = 0.0 if prev_nav in (None, 0) else (total_equity / prev_nav) - 1.0

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
            db.commit()

            # flush running metrics every 30 steps so the polling endpoint returns live data
            if len(nav_series) % 30 == 0 and len(nav_series) >= 5:
                interim = compute_run_eod_metrics(nav_series, return_series, trade_pnls=trade_pnls)
                run.cagr = interim.get("cagr")
                run.volatility = interim.get("volatility")
                run.sharpe = interim.get("sharpe")
                run.max_drawdown = interim.get("max_drawdown")
                run.win_rate = interim.get("win_rate")
                run.profit_factor = interim.get("profit_factor")
                mcl = interim.get("max_consecutive_losses")
                run.max_consecutive_losses = int(mcl) if mcl is not None else None
                run.n_trades = total_trades
                db.commit()

            # 4.5. process rollouts from DTE closes
            for (roll_strat, roll_zone, roll_n_contracts) in pending_rollouts:
                strat_factory = STRATEGY_BY_NAME.get(roll_strat)
                if strat_factory is None:
                    logger.warning(f"[ROLLOUT {date}] Unknown strategy {roll_strat}, skipping")
                    continue
                spec = strat_factory()
                s_cfg = (strategy_overrides or {}).get(roll_strat, {}).get(roll_zone, {})
                q = instrument.dividend_yield if instrument else 0.0
                try:
                    rolled = spec.builder(
                        date=date,
                        S=S,
                        iv=iv,
                        dte_days=45,
                        quantity=roll_n_contracts,
                        q=q,
                        target_delta_short=s_cfg.get("delta_short", 0.16),
                        target_delta_long=s_cfg.get("delta_long", 0.05),
                        target_delta_long_call=s_cfg.get("delta_long_call", 0.10),
                    )
                except Exception as exc:
                    logger.warning(f"[ROLLOUT {date}] Build failed for {roll_strat}: {exc}")
                    continue
                rolled.entry_zone = roll_zone

                roll_ev = None
                if instrument is not None:
                    legs_for_roll_ev = [
                        {
                            "strike": leg.state.K,
                            "type": leg.state.option_type,
                            "position": "short" if leg.sign == -1 else "long",
                            "qty": leg.quantity,
                        }
                        for leg in rolled.legs
                    ]
                    try:
                        roll_ev = compute_trade_ev(
                            legs=legs_for_roll_ev,
                            S=S,
                            T=45 / 365.0,
                            r=0.03,
                            sigma=iv,
                            instrument=instrument,
                        )
                    except Exception:
                        roll_ev = None

                portfolio.open_position(rolled)
                if roll_ev is not None:
                    portfolio.apply_entry_commission(roll_ev.transaction_costs)

                new_positions_count += 1
                total_trades += 1

                db_roll = BacktestPosition(
                    run_id=run.id,
                    position_type=roll_strat,
                    status="OPEN",
                    opened_at=date,
                    entry_underlying=S,
                    entry_iv=iv,
                    entry_macro_regime=row.get("macro_regime"),
                    initial_value=rolled.initial_value,
                    entry_conditions={"rollout": True, "underlying_price": S, "iv": float(iv)},
                    entry_fair_value=roll_ev.fair_value if roll_ev else None,
                    entry_ev_gross=roll_ev.expected_value_gross if roll_ev else None,
                    entry_ev_net=roll_ev.expected_value_net if roll_ev else None,
                    entry_prob_profit=roll_ev.prob_profit if roll_ev else None,
                    entry_transaction_costs=roll_ev.transaction_costs if roll_ev else None,
                    entry_max_loss=roll_ev.max_loss if roll_ev else None,
                    entry_max_profit=roll_ev.max_profit if roll_ev else None,
                )
                db.add(db_roll)
                db.flush()
                position_ids[id(rolled)] = db_roll.id
                db.commit()
                logger.warning(f"[ROLLOUT OPENED {date}] {roll_strat} zone={roll_zone} n_contracts={roll_n_contracts}")

            # 5. entry logic - only check when portfolio is empty
            has_open_positions = len([p for p in portfolio.positions if p.is_open]) > 0

            if not has_open_positions:
                logger.warning(f"[ENTRY CHECK {date}] Portfolio empty, checking for entry. IV={iv:.2f}, IV_RANK={row.get('iv_rank', 'N/A')}, ADX={row.get('adx', 'N/A')}, RSI={row.get('rsi_14', 'N/A')}")

                # Decision Engine L1-L5 pipeline
                decision = engine.process_signal(
                    row=row,
                    entry_config=entry_config or {},
                    position_config=position_config or {},
                    risk_config=risk_config or {},
                    strategy_overrides=strategy_overrides or {},
                )

                logger.warning(f"[L5 DECISION {date}] Action={decision.action.value}, Score={decision.score:.1f}, Reasoning={decision.reasoning}")

                if decision.action.value == "OPEN" and decision.strategy_spec is None:
                    logger.error(f"[L5 ERROR {date}] Action is OPEN but strategy_spec is None! Reasoning: {decision.reasoning}")
                    continue

                strategy = cast(Any, decision.strategy_spec)

                iv_rank_val = row.get("iv_rank")
                adx_val = row.get("adx")
                strategy_name_log = strategy.name if strategy else "N/A"
                size_multiplier_log = strategy.size_multiplier if strategy else 0.0

                if strategy:
                    logger.warning(f"[ENTRY RESULT {date}] Strategy={strategy_name_log}, size_multiplier={size_multiplier_log:.0%}")
                else:
                    logger.warning(f"[ENTRY DECISION {date}] Action={decision.action.value}, no strategy (as expected)")

                ev = decision.evaluation
                trend_raw = row.get("trend_signal")
                trend_log = str(int(trend_raw)) if trend_raw is not None else None

                decision_log = DecisionLog(
                    run_id=run.id,
                    date=date,
                    zone=decision.zone,
                    trend=trend_log,
                    iv_rank=float(iv_rank_val) if iv_rank_val is not None else None,
                    adx=float(adx_val) if adx_val is not None else None,
                    entry_score=float(row.get("entry_score", 50.0)),
                    strategy_name=strategy_name_log,
                    size_multiplier=size_multiplier_log,
                    should_trade=True,
                    spot=float(row.get("close", 0)),
                    iv=float(row.get("iv", 0)),
                    dte_days=int(row.get("dte_days", 45)),
                    delta=None,
                    gamma=None,
                    vega=None,
                    theta=None,
                    bid_ask_spread=None,
                    bid_ask_pct=None,
                    edge=None,
                    breakeven_distance=None,
                    edge_source=decision.edge_source,
                    decision_action=decision.action.value,
                    decision_score=decision.score,
                    decision_reasoning=decision.reasoning,
                    pricing_edge_score=ev.pricing_edge_score if ev else None,
                    risk_reward_score=ev.risk_reward_score if ev else None,
                    breakeven_score=ev.breakeven_score if ev else None,
                    execution_cost_score=ev.execution_cost_score if ev else None,
                    capital_efficiency_score=ev.capital_efficiency_score if ev else None,
                    iv_term_slope_delta5=_float_or_none(row.get("iv_term_slope_delta5")),
                    credit_spread_delta5=_float_or_none(row.get("credit_spread_delta5")),
                    vvix_rank=_float_or_none(row.get("vvix_rank")),
                )
                db.add(decision_log)
                db.commit()

                if not strategy:
                    continue

                # Check cooldown: strategy cannot reopen within cooldown_days
                cooldown_days_param = entry_config.get("entry.cooldown_days") if entry_config else None
                cooldown_days = int(cooldown_days_param["value"]) if cooldown_days_param else 5

                in_cooldown = False
                if strategy.name in recent_closes:
                    days_since_close = (datetime.datetime.strptime(date, "%Y-%m-%d") -
                                       datetime.datetime.strptime(recent_closes[strategy.name], "%Y-%m-%d")).days
                    if days_since_close < cooldown_days:
                        in_cooldown = True
                        logger.warning(f"[ENTRY COOLDOWN {date}] Strategy {strategy.name} in cooldown ({days_since_close} days < {cooldown_days})")

                should_open = decision.action.value == "OPEN" and not in_cooldown

                if should_open:
                    logger.warning(f"[ENTRY ACCEPT {date}] Opening position")
                    q = instrument.dividend_yield if instrument else 0.0
                    _entry_zone = decision.zone or ""
                    s_cfg = (strategy_overrides or {}).get(strategy.name, {}).get(_entry_zone, {})
                    new_position = strategy.builder(
                        date=date,
                        S=S,
                        iv=iv,
                        dte_days=45,
                        quantity=1,
                        q=q,
                        target_delta_short=s_cfg.get("delta_short", 0.16),
                        target_delta_long=s_cfg.get("delta_long", 0.05),
                        target_delta_long_call=s_cfg.get("delta_long_call", 0.10),
                    )
                    new_position.entry_zone = _entry_zone

                    # Compute EV with qty=1 to get per-contract max_loss for risk check
                    trade_ev = None
                    if instrument is not None:
                        legs_for_ev_1c = [
                            {
                                "strike": leg.state.K,
                                "type": leg.state.option_type,
                                "position": "short" if leg.sign == -1 else "long",
                                "qty": leg.quantity,
                            }
                            for leg in new_position.legs
                        ]
                        trade_ev = compute_trade_ev(
                            legs=legs_for_ev_1c,
                            S=S,
                            T=45 / 365.0,
                            r=0.03,
                            sigma=iv,
                            instrument=instrument,
                        )

                    # Risk-based sizing: Option B — block if even 1 contract exceeds budget
                    max_risk_pct = (position_config or {}).get("available_risk", 0.03)
                    budget = portfolio.cash * max_risk_pct
                    max_loss_1c = trade_ev.max_loss if trade_ev else None

                    if max_loss_1c is not None and max_loss_1c > 0 and budget > 0:
                        if max_loss_1c > budget:
                            logger.warning(
                                f"[RISK_REJECT {date}] max_loss={max_loss_1c:.2f} > budget={budget:.2f} "
                                f"(cash={portfolio.cash:.2f} × max_risk={max_risk_pct:.1%})"
                            )
                            decision_log.decision_action = "RISK_REJECT"
                            decision_log.decision_reasoning = (
                                f"RISK_REJECT: max_loss per contratto ({max_loss_1c:.2f}) > "
                                f"budget ({budget:.2f} = {portfolio.cash:.2f} × {max_risk_pct:.1%})"
                            )
                            db.commit()
                            continue

                        n_contracts = max(1, int(budget / max_loss_1c))
                        n_contracts = max(1, int(n_contracts * strategy.size_multiplier))
                        for leg in new_position.legs:
                            leg.quantity = n_contracts

                        # Recompute EV with final contract count
                        if instrument is not None:
                            legs_for_ev = [
                                {
                                    "strike": leg.state.K,
                                    "type": leg.state.option_type,
                                    "position": "short" if leg.sign == -1 else "long",
                                    "qty": leg.quantity,
                                }
                                for leg in new_position.legs
                            ]
                            trade_ev = compute_trade_ev(
                                legs=legs_for_ev,
                                S=S,
                                T=45 / 365.0,
                                r=0.03,
                                sigma=iv,
                                instrument=instrument,
                            )

                    logger.warning(f"open position: {new_position.name} {new_position.opened_at}")
                    portfolio.open_position(new_position)
                    if trade_ev is not None:
                        portfolio.apply_entry_commission(trade_ev.transaction_costs)

                    position_type_key = new_position.name.lower().replace(" ", "_")

                    ema_20 = row.get("ema_20")
                    sma_50 = row.get("sma_50")
                    trend = "UP" if (ema_20 is not None and sma_50 is not None and ema_20 > sma_50) else "DOWN"

                    entry_conditions = {
                        "underlying_price": S,
                        "iv": float(iv),
                        "iv_rv_ratio": float(row.get("iv_rv_ratio", 0)),
                        "rsi_14": float(row.get("rsi_14", 0)) if row.get("rsi_14") is not None else None,
                        "macd": float(row.get("macd", 0)) if row.get("macd") is not None else None,
                        "sma_20": float(row.get("sma_20", 0)) if row.get("sma_20") is not None else None,
                        "sma_50": float(row.get("sma_50", 0)) if row.get("sma_50") is not None else None,
                        "ema_20": float(row.get("ema_20", 0)) if row.get("ema_20") is not None else None,
                        "trend": trend,
                        "macro_regime": row.get("macro_regime"),
                        "macro_score": float(row.get("macro_score", 0)) if row.get("macro_score") is not None else None,
                        "rv_20": float(row.get("rv_20", 0)) if row.get("rv_20") is not None else None,
                    }

                    exit_conditions_entry = exit_config.copy() if exit_config else {}

                    db_position = BacktestPosition(
                        run_id=run.id,
                        position_type=position_type_key,
                        status="OPEN",
                        opened_at=date,
                        entry_underlying=S,
                        entry_iv=iv,
                        entry_macro_regime=row.get("macro_regime"),
                        initial_value=new_position.initial_value,
                        entry_conditions=entry_conditions,
                        exit_conditions=exit_conditions_entry,
                        entry_fair_value=trade_ev.fair_value if trade_ev else None,
                        entry_ev_gross=trade_ev.expected_value_gross if trade_ev else None,
                        entry_ev_net=trade_ev.expected_value_net if trade_ev else None,
                        entry_prob_profit=trade_ev.prob_profit if trade_ev else None,
                        entry_transaction_costs=trade_ev.transaction_costs if trade_ev else None,
                        entry_max_loss=trade_ev.max_loss if trade_ev else None,
                        entry_max_profit=trade_ev.max_profit if trade_ev else None,
                    )
                    db.add(db_position)
                    db.flush()

                    position_ids[id(new_position)] = db_position.id
                    total_trades += 1
                    db.commit()
                else:
                    logger.warning(f"[ENTRY REJECT {date}] decision={decision.action.value}, cooldown={in_cooldown}")
            else:
                logger.warning(f"[ENTRY SKIP {date}] Portfolio has open positions, skipping entry check")

        # successo
        metrics = compute_run_eod_metrics(nav_series, return_series, trade_pnls=trade_pnls)

        run.cagr = metrics["cagr"]
        run.volatility = metrics["volatility"]
        run.sharpe = metrics["sharpe"]
        run.max_drawdown = metrics["max_drawdown"]
        run.win_rate = metrics["win_rate"]
        run.profit_factor = metrics["profit_factor"]
        mcl = metrics.get("max_consecutive_losses")
        run.max_consecutive_losses = int(mcl) if mcl is not None else None
        run.n_trades = total_trades
        run.status = BacktestStatus.DONE
        run.error_message = None
        db.commit()
    except Exception as e:
        db.rollback()
        run.error_message = str(e)
        db.commit()
        raise
        


def execute_eod_backtest(db: Session, run: BacktestRun) -> None:
    logger.warning(f"[RUN {run.id}] execute_eod_backtest: Loading parameters")
    params = db.query(BacktestRunParameter).filter(BacktestRunParameter.run_id == run.id).all()
    if not params:
        error_msg = "Undefined params for backtest"
        run.error_message = error_msg
        db.commit()
        raise ValueError(error_msg)

    params_dict = {
        p.key: {
            "value": p.value,
            "unit": p.unit,
        }
        for p in params
    }
    logger.warning(f"[RUN {run.id}] Loaded {len(params)} parameters")

    logger.warning(f"[RUN {run.id}] Preparing market data")
    df = prepare_market_df(db, run)
    logger.warning(f"[RUN {run.id}] Market data loaded: {len(df)} rows")

    logger.warning(f"[RUN {run.id}] Building entry config (needed for entry_score in pipeline)")
    entry_config = _build_entry_config(params_dict)

    logger.warning(f"[RUN {run.id}] Building backtest dataset (with all indicators)")
    df = build_backtest_dataset(df, db, params_dict, run, entry_config=entry_config)
    logger.warning(f"[RUN {run.id}] Dataset built: {len(df)} rows, columns: {list(df.columns)[:10]}...")

    logger.warning(f"[RUN {run.id}] Dataset preview: {df.head()}")

    logger.warning(f"[RUN {run.id}] Extracting execution parameters")
    initial_capital = params_dict.get("initial_capital")
    initial_capital = float(initial_capital["value"]) if initial_capital else 0.0
    logger.warning(f"[RUN {run.id}] Initial capital: {initial_capital}")

    days = params_dict.get("entry_every_n_days")
    entry_every_n_days = int(days["value"]) if days is not None else 30
    logger.warning(f"[RUN {run.id}] Entry every N days: {entry_every_n_days}")

    ticker_param = params_dict.get("ticker")
    ticker = ticker_param["value"] if ticker_param else "IWM"
    logger.warning(f"[RUN {run.id}] Ticker: {ticker}")

    logger.warning(f"[RUN {run.id}] Loading instrument config")
    instrument = get_instrument_config(db, ticker)
    if instrument is not None:
        comm_per_contract_p = params_dict.get("cost_model.commission_per_contract")
        min_commission_p = params_dict.get("cost_model.min_commission")
        if comm_per_contract_p:
            instrument.cost_model.commission_per_contract = float(comm_per_contract_p["value"])
        if min_commission_p:
            instrument.cost_model.min_commission = float(min_commission_p["value"])
    logger.warning(f"[RUN {run.id}] Instrument loaded: {instrument}")
    logger.warning(f"[RUN {run.id}] Building exit config")
    exit_config = _build_exit_config(params_dict)
    # entry_config already built above (before build_backtest_dataset, needed for entry_score column)
    logger.warning(f"[RUN {run.id}] Building position config")
    position_config = _build_position_config(params_dict)
    logger.warning(f"[RUN {run.id}] Building risk config (Decision Layer)")
    risk_config = _build_risk_config(params_dict)

    # Parse per-strategy config overrides (strategy_config.overrides)
    strategy_overrides: dict = {}
    overrides_param = params_dict.get("strategy_config.overrides")
    if overrides_param:
        try:
            strategy_overrides = json.loads(overrides_param["value"])
        except (json.JSONDecodeError, KeyError):
            logger.warning(f"[RUN {run.id}] strategy_config.overrides is not valid JSON, ignoring")

    # Parse rollout config
    rollout_config: dict = {}
    rollout_enabled_p = params_dict.get("rollout.enabled")
    if rollout_enabled_p and rollout_enabled_p["value"].lower() == "true":
        rollout_config["enabled"] = True
        rollout_min_p = params_dict.get("rollout.min_profit_pct")
        if rollout_min_p:
            rollout_config["min_profit_pct"] = float(rollout_min_p["value"])

    logger.warning(f"[RUN {run.id}] Starting EOD backtest execution with {len(df)} data points")
    run_eod_backtest(
        db,
        run,
        df,
        initial_cash=initial_capital,
        entry_every_n_days=entry_every_n_days,
        instrument=instrument,
        exit_config=exit_config,
        entry_config=entry_config,
        position_config=position_config,
        risk_config=risk_config,
        strategy_overrides=strategy_overrides,
        rollout_config=rollout_config,
    )
    logger.warning(f"[RUN {run.id}] EOD backtest execution completed")


def run_in_background(run_id: int) -> None:
    """Entry point per il thread background. Crea la propria sessione DB."""
    logger.warning(f"[RUN {run_id}] Starting background backtest execution")
    db = SessionLocal()
    try:
        logger.warning(f"[RUN {run_id}] Loading backtest run from DB")
        run = db.query(BacktestRun).filter(BacktestRun.id == run_id).first()

        if not run:
            raise HTTPException(status_code=404, detail="Backtest not found")

        logger.warning(f"[RUN {run_id}] Backtest frequency: {run.frequency}")
        if run.frequency == BacktestFrequency.EOM:
            logger.warning(f"[RUN {run_id}] Executing EOM backtest")
            execute_eom_backtest(db, run)
        elif run.frequency == BacktestFrequency.EOD:
            logger.warning(f"[RUN {run_id}] Executing EOD backtest")
            execute_eod_backtest(db, run)
        else:
            raise HTTPException(status_code=400, detail="Backtest frequency not yet implemented")

        logger.warning(f"[RUN {run_id}] ✅ Backtest completed successfully")
    except Exception as e:
        error_msg = str(e) if str(e) else f"Unknown error (type: {type(e).__name__})"
        logger.error(f"[RUN {run_id}] ❌ Background error: {error_msg}", exc_info=True)
        print(f"\n[RUN {run_id}] DETAILED ERROR TRACEBACK:\n{traceback.format_exc()}\n")

        # Salva l'errore nel database
        try:
            if run:
                db.refresh(run)
                run.error_message = error_msg
                run.status = BacktestStatus.ERROR
                db.commit()
        except Exception as db_error:
            logger.error(f"[RUN {run_id}] Could not save error to DB: {db_error}")
    finally:
        try:
            db.close()
        except Exception as close_error:
            logger.error(f"[RUN {run_id}] Error closing DB session: {close_error}")
        
