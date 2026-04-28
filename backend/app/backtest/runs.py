import datetime
import json
import math
import traceback
from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import Any, cast
import pandas as pd
import logging
from app.backtest.domain.strategy.exit_context import ExitContext
from app.backtest.domain.strategy.exit_rules import should_close
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
from app.backtest.metrics import compute_metrics, compute_run_eod_metrics
from .domain.models import Portfolio
from app.backtest.data_preparation.base import prepare_market_df
from app.backtest.data_preparation.pipeline import build_backtest_dataset
from app.backtest.domain.strategy.selectors import select_strategy
from app.backtest.domain.option.ev import compute_trade_ev

logger = logging.getLogger(__name__)


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
    entry_every_n_days: int = 30,
    instrument=None,
    exit_config: dict | None = None,
    entry_config: dict | None = None,
    target_delta_short: float | None = None,
    target_delta_long: float | None = None,
) -> None:
    if target_delta_short is None or target_delta_long is None:
        raise ValueError(
            "target_delta_short e target_delta_long sono obbligatori. "
            "Aggiungili come BacktestRunParameter (entry.target_delta_short, entry.target_delta_long)."
        )

    cleanup_eod_backtest_run(db, run.id)

    logger.warning(f"Start backtest execution -> {df.tail()}")
    try:
        portfolio = Portfolio(initial_cash=initial_cash)
        position_ids: dict[int,int] = {}

        nav_series: list[float] = []
        return_series: list[float] = []
        prev_nav: float | None = None
        total_trades = 0
        recent_closes: dict[str, str] = {}  # Track strategy close dates for cooldown

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
                db.commit()

            # 3. close logic
            for position in portfolio.positions:
                should_exit, exit_conditions = should_close(ExitContext(
                    position=position,
                    row=row,
                    exit_config=exit_config or {},
                ))
                if position.is_open and should_exit:
                    exit_reason = exit_conditions.get("triggered_by") if exit_conditions else "unknown"
                    logger.warning(f"close position: {position.name} {position.opened_at} - reason: {exit_reason}")
                    portfolio.close_position(position)
                    closed_positions_count += 1
                    # Track the close date for this strategy (cooldown)
                    recent_closes[position.name] = date

                db_position_id = position_ids.get(id(position))
                if db_position_id is not None:
                    db_position = db.get(BacktestPosition,db_position_id)
                    if db_position:
                        db_position.status = "CLOSED"
                        db_position.closed_at = date
                        db_position.close_value = position.price
                        db_position.realized_pnl = position.pnl
                        if exit_conditions:
                            db_position.exit_conditions = exit_conditions
                db.commit()

            portfolio.remove_closed_positions()

            # 4. entry logic - only check when portfolio is empty
            has_open_positions = len([p for p in portfolio.positions if p.is_open]) > 0

            if not has_open_positions:
                logger.warning(f"[ENTRY CHECK {date}] Portfolio empty, checking for entry. IV={iv:.2f}, IV_RANK={row.get('iv_rank', 'N/A')}, ADX={row.get('adx', 'N/A')}, RSI={row.get('rsi_14', 'N/A')}")
                strategy = select_strategy(row, entry_config or {})
                logger.warning(f"[ENTRY RESULT {date}] Strategy={strategy.name}, should_trade={strategy.should_trade}, size_multiplier={strategy.size_multiplier:.0%}")

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

                if strategy.should_trade and strategy.size_multiplier > 0 and not in_cooldown:
                    logger.warning(f"[ENTRY ACCEPT {date}] Opening position")
                    q = instrument.dividend_yield if instrument else 0.0
                    new_position = strategy.builder(
                        date=date,
                        S=S,
                        iv=iv,
                        dte_days=45,
                        quantity=1,
                        q=q,
                        target_delta_short=target_delta_short,
                        target_delta_long=target_delta_long,
                    )

                    # Apply size multiplier (quality-based sizing from entry score)
                    if strategy.size_multiplier < 1.0:
                        _scale_position(new_position, strategy.size_multiplier)

                    # Calcolo EV pre-trade — filtra solo se ha edge netto
                    trade_ev = None
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
                        if not trade_ev.is_credit:
                            logger.warning(f"Skip position (debit trade): net_premium={trade_ev.net_premium:.2f}")
                            continue

                    logger.warning(f"open position: {new_position.name} {new_position.opened_at}")
                    portfolio.open_position(new_position)
                    new_positions_count += 1

                    # Converti position_type in snake_case per FK a option_strategies
                    position_type_key = new_position.name.lower().replace(" ", "_")

                    # Capture entry conditions from row
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

                    # Capture exit conditions rules - use actual exit_config from run parameters
                    exit_conditions = exit_config.copy() if exit_config else {}

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
                        exit_conditions=exit_conditions,
                        entry_fair_value=trade_ev.fair_value if trade_ev else None,
                        entry_ev_gross=trade_ev.expected_value_gross if trade_ev else None,
                        entry_ev_net=trade_ev.expected_value_net if trade_ev else None,
                        entry_prob_profit=trade_ev.prob_profit if trade_ev else None,
                        entry_transaction_costs=trade_ev.transaction_costs if trade_ev else None,
                    )
                    db.add(db_position)
                    db.flush() # serve per ottenere db_position.id

                    position_ids[id(new_position)] = db_position.id
                    total_trades += 1
                    db.commit()
                else:
                    reason = "should_trade=False" if not strategy.should_trade else "size_multiplier=0"
                    logger.warning(f"[ENTRY REJECT {date}] {reason}")
            else:
                logger.warning(f"[ENTRY SKIP {date}] Portfolio has open positions, skipping entry check")

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

    logger.warning(f"[RUN {run.id}] Building backtest dataset (with all indicators)")
    df = build_backtest_dataset(df, db, params_dict, run)
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
    logger.warning(f"[RUN {run.id}] Instrument loaded: {instrument}")
    logger.warning(f"[RUN {run.id}] Building exit config")
    exit_config = _build_exit_config(params_dict)
    logger.warning(f"[RUN {run.id}] Building entry config")
    entry_config = _build_entry_config(params_dict)

    logger.warning(f"[RUN {run.id}] Extracting delta parameters")
    delta_short_param = params_dict.get("entry.target_delta_short")
    delta_long_param = params_dict.get("entry.target_delta_long")
    if delta_short_param is None or delta_long_param is None:
        missing = []
        if delta_short_param is None:
            missing.append("entry.target_delta_short")
        if delta_long_param is None:
            missing.append("entry.target_delta_long")
        raise ValueError(
            f"Parametri obbligatori mancanti per la strike selection: {', '.join(missing)}. "
            "Aggiungili nella configurazione del run (es. target_delta_short=0.16, target_delta_long=0.05)."
        )
    target_delta_short = float(delta_short_param["value"])
    target_delta_long = float(delta_long_param["value"])
    logger.warning(f"[RUN {run.id}] Target deltas: short={target_delta_short}, long={target_delta_long}")

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
        target_delta_short=target_delta_short,
        target_delta_long=target_delta_long,
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
        
