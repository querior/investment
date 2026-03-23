from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
import math
import pandas as pd
from app.db.session import SessionLocal
from app.db.macro_raw import MacroRaw
from app.db.macro_processed import MacroProcessed
from app.db.macro_pillar import MacroPillar
from app.db.market_price import MarketPrice
from app.services.config_repo import (
    get_indicator_meta,
    get_market_symbol_meta,
    get_processed_meta,
    get_pillar_meta,
    get_macro_score_weights,
    get_regime_thresholds,
    get_composite_score_meta,
)

router = APIRouter(tags=["data"])


def _get_regime(score: float | None, thresholds: list[tuple[float | None, str]]) -> str:
    if score is None or not math.isfinite(score):
        return "N/A"
    for threshold_min, label in thresholds:
        actual_min = threshold_min if threshold_min is not None else float("-inf")
        if score > actual_min:
            return label
    return "N/A"


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/data/catalog")
def get_catalog(
    page: int = 1,
    limit: int = 10,
    data_category: str = "raw",
    orderBy: str = "symbol",
    filter: str | None = None,
    db: Session = Depends(get_db),
):
    filter_val = filter if filter and filter != "undefined" else None

    macro_raw_rows  = _query_macro_raw(db, filter_val)
    macro_proc_rows = _query_macro_processed(db, filter_val)
    pillar_rows     = _query_pillars(db, filter_val)
    scores_rows     = _query_scores(db, filter_val)
    market_rows     = _query_market(db, filter_val)

    category_map = {
        "macro_raw":       macro_raw_rows,
        "macro_processed": macro_proc_rows,
        "pillars":         pillar_rows,
        "scores":          scores_rows,
        "market":          market_rows,
    }

    active_category = data_category if data_category in category_map else "macro_raw"
    rows = category_map[active_category]
    if orderBy == "symbol":
        rows.sort(key=lambda r: r["symbol"])

    return {
        "items": _paginate(rows, page, limit),
        "active_category": active_category,
        "counters": {
            "macro_raw":       len(macro_raw_rows),
            "macro_processed": len(macro_proc_rows),
            "pillars":         len(pillar_rows),
            "scores":          len(scores_rows),
            "market":          len(market_rows),
        },
    }


def _filter_rows(rows: list[dict], filter_val: str | None) -> list[dict]:
    if not filter_val:
        return rows
    f = filter_val.upper()
    return [
        r for r in rows
        if f in r["symbol"].upper()
        or f in r["description"].upper()
        or (r.get("formula") and f in r["formula"].upper())
    ]


def _query_macro_raw(db: Session, filter_val: str | None) -> list[dict]:
    agg = {
        r.symbol: r
        for r in db.query(
            MacroRaw.indicator.label("symbol"),
            MacroRaw.source,
            func.min(MacroRaw.date).label("first_date"),
            func.max(MacroRaw.date).label("last_date"),
            func.count(MacroRaw.date).label("row_count"),
        )
        .group_by(MacroRaw.indicator, MacroRaw.source)
        .all()
    }

    macro_meta = get_indicator_meta(db)
    rows = []
    for symbol, meta in macro_meta.items():
        r = agg.get(symbol)
        rows.append({
            "id": f"macro_raw:{symbol}",
            "symbol": symbol,
            "description": meta.get("description", ""),
            "formula": None,
            "source": r.source if r else meta.get("source", "FRED"),
            "frequency": meta.get("frequency", ""),
            "first_date": str(r.first_date) if r and r.first_date else None,
            "last_date": str(r.last_date) if r and r.last_date else None,
            "row_count": r.row_count if r else 0,
            "data_category": "macro_raw",
        })

    return _filter_rows(rows, filter_val)


def _query_macro_processed(db: Session, filter_val: str | None) -> list[dict]:
    agg = {
        r.symbol: r
        for r in db.query(
            MacroProcessed.indicator.label("symbol"),
            func.min(MacroProcessed.date).label("first_date"),
            func.max(MacroProcessed.date).label("last_date"),
            func.count(MacroProcessed.date).label("row_count"),
        )
        .group_by(MacroProcessed.indicator)
        .all()
    }

    processed_meta = get_processed_meta(db)
    rows = []
    for symbol, meta in processed_meta.items():
        r = agg.get(symbol)
        rows.append({
            "id": f"macro_processed:{symbol}",
            "symbol": symbol,
            "description": meta.get("description", ""),
            "formula": meta.get("formula"),
            "source": "internal",
            "frequency": meta.get("frequency", ""),
            "first_date": str(r.first_date) if r and r.first_date else None,
            "last_date": str(r.last_date) if r and r.last_date else None,
            "row_count": r.row_count if r else 0,
            "data_category": "macro_processed",
        })

    return _filter_rows(rows, filter_val)


def _query_pillars(db: Session, filter_val: str | None) -> list[dict]:
    agg = {
        r.symbol: r
        for r in db.query(
            MacroPillar.pillar.label("symbol"),
            func.min(MacroPillar.date).label("first_date"),
            func.max(MacroPillar.date).label("last_date"),
            func.count(MacroPillar.date).label("row_count"),
        )
        .group_by(MacroPillar.pillar)
        .all()
    }

    pillar_meta = get_pillar_meta(db)
    rows = []
    for pillar, meta in pillar_meta.items():
        r = agg.get(pillar)
        rows.append({
            "id": f"pillar:{pillar}",
            "symbol": pillar,
            "description": meta["description"],
            "formula": meta["formula"],
            "source": "internal",
            "frequency": meta["frequency"],
            "first_date": str(r.first_date) if r and r.first_date else None,
            "last_date": str(r.last_date) if r and r.last_date else None,
            "row_count": r.row_count if r else 0,
            "data_category": "pillar",
        })

    return _filter_rows(rows, filter_val)


def _query_scores(db: Session, filter_val: str | None) -> list[dict]:
    score_weights = get_macro_score_weights(db)
    score_meta = get_composite_score_meta(db)
    required_pillars = set(score_weights.keys())

    all_rows = (
        db.query(MacroPillar.date, MacroPillar.pillar)
        .filter(MacroPillar.pillar.in_(required_pillars))
        .all()
    )

    empty_row = {
        "id": "scores:MacroScore",
        "symbol": "MacroScore",
        "description": score_meta.get("description", ""),
        "formula": score_meta.get("formula", ""),
        "source": "internal",
        "frequency": "MONTHLY",
        "first_date": None,
        "last_date": None,
        "row_count": 0,
        "data_category": "scores",
    }

    if not all_rows:
        return _filter_rows([empty_row], filter_val)

    df = pd.DataFrame(all_rows, columns=["date", "pillar"])
    complete_dates = (
        df.groupby("date")["pillar"]
        .apply(set)
        .pipe(lambda s: s[s.apply(lambda p: p == required_pillars)])
        .index.sort_values()
        .tolist()
    )

    return _filter_rows([{
        **empty_row,
        "first_date": str(complete_dates[0]) if complete_dates else None,
        "last_date": str(complete_dates[-1]) if complete_dates else None,
        "row_count": len(complete_dates),
    }], filter_val)


def _query_market(db: Session, filter_val: str | None) -> list[dict]:
    agg = {
        r.symbol: r
        for r in db.query(
            MarketPrice.symbol,
            MarketPrice.source,
            func.min(MarketPrice.date).label("first_date"),
            func.max(MarketPrice.date).label("last_date"),
            func.count(MarketPrice.date).label("row_count"),
        )
        .group_by(MarketPrice.symbol, MarketPrice.source)
        .all()
    }

    market_meta = get_market_symbol_meta(db)
    rows = []
    for symbol, meta in market_meta.items():
        r = agg.get(symbol)
        rows.append({
            "id": f"market:{symbol}",
            "symbol": symbol,
            "description": meta.get("description", ""),
            "formula": None,
            "source": r.source if r else meta.get("source", "YAHOO"),
            "frequency": meta.get("frequency", ""),
            "first_date": str(r.first_date) if r and r.first_date else None,
            "last_date": str(r.last_date) if r and r.last_date else None,
            "row_count": r.row_count if r else 0,
            "data_category": "market",
        })

    return _filter_rows(rows, filter_val)


def _paginate(rows: list[dict], page: int, limit: int) -> list[dict]:
    start = (page - 1) * limit
    return rows[start: start + limit]


@router.get("/data/series")
def get_series(
    symbol: str,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
):
    LIMIT = 1000

    # macro score
    if symbol == "MacroScore":
        score_weights = get_macro_score_weights(db)
        regime_thresholds = get_regime_thresholds(db)
        required_pillars = set(score_weights.keys())

        q = (
            db.query(MacroPillar.date, MacroPillar.pillar, MacroPillar.score)
            .filter(MacroPillar.pillar.in_(required_pillars))
        )
        if start_date:
            q = q.filter(MacroPillar.date >= start_date)
        if end_date:
            q = q.filter(MacroPillar.date <= end_date)

        all_rows = q.order_by(MacroPillar.date).all()
        if not all_rows:
            raise HTTPException(status_code=404, detail="Nessun dato disponibile per MacroScore")

        df = pd.DataFrame(all_rows, columns=["date", "pillar", "score"])
        complete_mask = (
            df.groupby("date")["pillar"]
            .apply(set)
            .pipe(lambda s: s[s.apply(lambda p: p == required_pillars)])
            .index
        )
        df = df[df["date"].isin(complete_mask)]

        if df.empty:
            raise HTTPException(status_code=404, detail="Nessuna data con tutti i pillar disponibili")

        pivot = df.pivot(index="date", columns="pillar", values="score")
        pivot["MacroScore"] = sum(pivot[p] * w for p, w in score_weights.items())
        pivot["regime"] = pivot["MacroScore"].apply(lambda v: _get_regime(v, regime_thresholds))
        pivot = pivot.tail(LIMIT).reset_index()

        points = []
        for _, row in pivot.iterrows():
            score = float(row["MacroScore"])  # type: ignore[arg-type]
            if math.isfinite(score):
                points.append({
                    "date": str(row["date"]),
                    "value": round(score, 6),
                    "regime": str(row["regime"]),
                })

        dates = [p["date"] for p in points]
        score_meta = get_composite_score_meta(db)
        return {
            "symbol": "MacroScore",
            "description": score_meta.get("description", ""),
            "source": "internal",
            "frequency": "MONTHLY",
            "first_date": str(dates[0]) if dates else None,
            "last_date": str(dates[-1]) if dates else None,
            "row_count": len(dates),
            "data_category": "scores",
            "points": points,
        }

    # macro processed
    processed_meta = get_processed_meta(db)
    if symbol in processed_meta:
        agg = db.query(
            func.min(MacroProcessed.date), func.max(MacroProcessed.date), func.count(MacroProcessed.date)
        ).filter(MacroProcessed.indicator == symbol).first()
        if agg and agg[2] > 0:
            q = db.query(MacroProcessed.date, MacroProcessed.z_score).filter(MacroProcessed.indicator == symbol)
            if start_date:
                q = q.filter(MacroProcessed.date >= start_date)
            if end_date:
                q = q.filter(MacroProcessed.date <= end_date)
            rows = list(reversed(q.order_by(MacroProcessed.date.desc()).limit(LIMIT).all()))
            meta = processed_meta[symbol]
            return {
                "symbol": symbol,
                "description": meta.get("description", ""),
                "source": "internal",
                "frequency": meta.get("frequency", ""),
                "first_date": str(agg[0]) if agg[0] else None,
                "last_date": str(agg[1]) if agg[1] else None,
                "row_count": agg[2],
                "data_category": "macro_processed",
                "points": [{"date": str(r.date), "value": r.z_score} for r in rows if math.isfinite(r.z_score)],
            }

    # macro raw
    agg = db.query(
        func.min(MacroRaw.date), func.max(MacroRaw.date), func.count(MacroRaw.date), MacroRaw.source
    ).filter(MacroRaw.indicator == symbol).group_by(MacroRaw.source).first()
    if agg:
        q = db.query(MacroRaw.date, MacroRaw.value).filter(MacroRaw.indicator == symbol)
        if start_date:
            q = q.filter(MacroRaw.date >= start_date)
        if end_date:
            q = q.filter(MacroRaw.date <= end_date)
        rows = list(reversed(q.order_by(MacroRaw.date.desc()).limit(LIMIT).all()))
        macro_meta = get_indicator_meta(db)
        meta = macro_meta.get(symbol, {})
        return {
            "symbol": symbol,
            "description": meta.get("description", ""),
            "source": agg[3],
            "frequency": meta.get("frequency", ""),
            "first_date": str(agg[0]) if agg[0] else None,
            "last_date": str(agg[1]) if agg[1] else None,
            "row_count": agg[2],
            "data_category": "macro_raw",
            "points": [{"date": str(r.date), "value": r.value} for r in rows if math.isfinite(r.value)],
        }

    # market prices
    agg = db.query(
        func.min(MarketPrice.date), func.max(MarketPrice.date), func.count(MarketPrice.date), MarketPrice.source
    ).filter(MarketPrice.symbol == symbol).group_by(MarketPrice.source).first()
    if agg:
        q = db.query(MarketPrice.date, MarketPrice.close).filter(MarketPrice.symbol == symbol)
        if start_date:
            q = q.filter(MarketPrice.date >= start_date)
        if end_date:
            q = q.filter(MarketPrice.date <= end_date)
        rows = list(reversed(q.order_by(MarketPrice.date.desc()).limit(LIMIT).all()))
        market_meta = get_market_symbol_meta(db)
        meta = market_meta.get(symbol, {})
        return {
            "symbol": symbol,
            "description": meta.get("description", ""),
            "source": agg[3],
            "frequency": meta.get("frequency", ""),
            "first_date": str(agg[0]) if agg[0] else None,
            "last_date": str(agg[1]) if agg[1] else None,
            "row_count": agg[2],
            "data_category": "market",
            "points": [{"date": str(r.date), "value": r.close} for r in rows if math.isfinite(r.close)],
        }

    # pillar scores
    agg = db.query(
        func.min(MacroPillar.date), func.max(MacroPillar.date), func.count(MacroPillar.date)
    ).filter(MacroPillar.pillar == symbol).first()
    if agg and agg[2] > 0:
        q = db.query(MacroPillar.date, MacroPillar.score).filter(MacroPillar.pillar == symbol)
        if start_date:
            q = q.filter(MacroPillar.date >= start_date)
        if end_date:
            q = q.filter(MacroPillar.date <= end_date)
        rows = list(reversed(q.order_by(MacroPillar.date.desc()).limit(LIMIT).all()))
        pillar_meta = get_pillar_meta(db)
        meta = pillar_meta.get(symbol, {})
        return {
            "symbol": symbol,
            "description": meta.get("description", ""),
            "source": "internal",
            "frequency": meta.get("frequency", ""),
            "first_date": str(agg[0]) if agg[0] else None,
            "last_date": str(agg[1]) if agg[1] else None,
            "row_count": agg[2],
            "data_category": "pillar",
            "points": [{"date": str(r.date), "value": r.score} for r in rows if math.isfinite(r.score)],
        }

    raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")
