from datetime import date
from typing import cast
from sqlalchemy.orm import Session
from app.backtest.schemas import (
    BacktestRun,
    BacktestWeight,
    BacktestPerformance,
)
from app.backtest.loaders import load_asset_returns
from app.services.allocation.engine import compute_allocation
from app.db.macro_pillar import MacroPillar
from app.backtest.metrics import compute_metrics

def load_nav_series(db, run_id: int) -> list[float]:
  rows = (
    db.query(BacktestPerformance)
    .filter(BacktestPerformance.run_id == run_id)
    .order_by(BacktestPerformance.date)
    .all()
  )
  return [r.nav for r in rows]


def run_backtest(
  db: Session,
  name: str,
  strategy_version: str,
  start: date,
  end: date,
) -> int:
    run = BacktestRun(
      name=name,
      strategy_version=strategy_version,
      start_date=start,
      end_date=end,
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    returns = load_asset_returns(db, start, end)

    nav = 1.0
    prev_weights = None

    dates = sorted(returns.keys())

    for i in range(len(dates) - 1):
        d = dates[i]
        next_d = dates[i + 1]

        pillars_rows = (
          db.query(MacroPillar)
          .filter(MacroPillar.date == d)
          .all()
        )
        if not pillars_rows:
            continue

        pillars = {r.pillar: r.score for r in pillars_rows}
        weights = compute_allocation(pillars)

        # salva pesi
        for asset, w in weights.items():
            db.add(
              BacktestWeight(
                run_id=run.id,
                date=next_d,
                asset=asset,
                weight=w,
              )
            )

        # calcola return portafoglio
        ret = 0.0
        for asset, w in weights.items():
            asset_ret = returns[next_d].get(asset, 0.0)
            ret += w * asset_ret

        nav *= (1 + ret)

        db.add(
            BacktestPerformance(
              run_id=run.id,
              date=next_d,
              nav=nav,
              monthly_return=ret,
            )
        )

    db.commit()
    
    
    metrics = compute_metrics(load_nav_series(db, run.id)) # type: ignore
    if not metrics:
      return cast(int, run.id)
    run.cagr = metrics["cagr"]
    run.volatility = metrics["volatility"]
    run.sharpe = metrics["sharpe"]
    run.max_drawdown = metrics["max_drawdown"]
    db.commit()
    
    print(
      f"[BACKTEST {run.id}] "
      f"CAGR={run.cagr:.2%} | "
      f"Vol={run.volatility:.2%} | "
      f"Sharpe={run.sharpe:.2f} | "
      f"MaxDD={run.max_drawdown:.2%}"
    )
    
    
    return run.id # type: ignore[return-value]
