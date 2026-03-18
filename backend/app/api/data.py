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
from app.services.processed.config import PROCESSED_MAP
from app.services.pillars.config import PILLARS

router = APIRouter(tags=["data"])

# Serie raw scaricate direttamente da FRED
MACRO_META = {
    "CUMFNS":   {"description": "Capacity Utilization: Manufacturing",                          "frequency": "MONTHLY"},
    "GDPC1":    {"description": "Real Gross Domestic Product",                                  "frequency": "QUARTERLY"},
    "W875RX1":  {"description": "Real personal income excluding current transfer receipts",     "frequency": "MONTHLY"},    
    "INDPRO":   {"description": "Industrial Production Index",                                  "frequency": "MONTHLY"},
    "CPIAUCSL": {"description": "Consumer Price Index (All Urban)",                             "frequency": "MONTHLY"},
    "PPIFIS":   {"description": "Producer Price Index",                                         "frequency": "MONTHLY"},
    "PPIACO":   {"description": "Producer Price Index by Commodity: All Commodities",           "frequency": "MONTHLY"},
    "EXPINF5YR":{"description": "5-Year Expected Inflation",                                    "frequency": "MONTHLY"},
    "T5YIE":    {"description": "5-Year Breakeven Inflation Rate",                              "frequency": "DAILY"},
    "FEDFUNDS": {"description": "Federal Funds Effective Rate",                                 "frequency": "MONTHLY"},
    "T10Y2Y":   {"description": "10-Year Treasury Minus 2-Year Treasury",                       "frequency": "DAILY"},
    "VIXCLS":   {"description": "CBOE Volatility Index (VIX)",                                  "frequency": "DAILY"},
    "BAA10Y":   {"description": "Moody's Baa Corporate Bond Spread",                            "frequency": "DAILY"},
    "NFCI":     {"description": "Chicago Fed National Financial Conditions",                    "frequency": "WEEKLY"},
}

_TRANSFORM_LABEL = {
    "yoy":   "YoY % change",
    "level": "level",
    "delta": "monthly delta",
}

_TRANSFORM_FORMULA = {
    "yoy":   "(xₜ / xₜ₋₁₂ − 1) × 100  →  z = (x − μ₆₀) / σ₆₀, clip ±3",
    "level": "xₜ − xₜ₋₁  →  z = (x − μ₆₀) / σ₆₀, clip ±3",
    "delta": "xₜ − xₜ₋₁  →  z = (x − μ₆₀) / σ₆₀, clip ±3",
}

# Serie derivate da process_indicator (z-score su raw o trasformazioni)
PROCESSED_META: dict[str, dict] = {}
for _src, _tgt, _tf in PROCESSED_MAP:
    _src_desc = MACRO_META.get(_src, {}).get("description", _src)
    PROCESSED_META[_tgt] = {
        "description": f"{_src_desc} — {_TRANSFORM_LABEL.get(_tf, _tf)}",
        "formula": _TRANSFORM_FORMULA.get(_tf, ""),
        "source_indicator": _src,
        "transform": _tf,
        "frequency": MACRO_META.get(_src, {}).get("frequency", "MONTHLY"),
    }

MARKET_META = {
    "SPY": {"description": "S&P 500 ETF (Equity)",                           "frequency": "DAILY"},
    "IEF": {"description": "iShares 7-10 Year Treasury Bond ETF (Bond)",     "frequency": "DAILY"},
    "DBC": {"description": "Invesco DB Commodity Index Tracking Fund",       "frequency": "DAILY"},
    "BIL": {"description": "SPDR Bloomberg 1-3 Month T-Bill ETF (Cash)",     "frequency": "DAILY"},
}

_PILLAR_LABEL = {
    "Growth":    "Forza del ciclo economico reale",
    "Inflation": "Pressione inflattiva realizzata e attesa",
    "Policy":    "Stance della banca centrale (Fed)",
    "Risk":      "Stress finanziario e risk aversion",
}

PILLAR_META: dict[str, dict] = {}
for _pillar, _indicators in PILLARS.items():
    PILLAR_META[_pillar] = {
        "description": _PILLAR_LABEL.get(_pillar, _pillar),
        "formula": "mean(" + ", ".join(f"z({ind})" for ind in _indicators) + ")",
        "frequency": "MONTHLY",
    }

MACRO_SCORE_WEIGHTS = {
    "Growth":    0.3,
    "Inflation": -0.3,
    "Policy":    -0.2,
    "Risk":      -0.2,
}

def _build_score_formula(weights: dict) -> str:
    parts = []
    for pillar, w in weights.items():
        sign = "+" if w >= 0 else "−"
        parts.append(f"{sign} {abs(w)}·{pillar}")
    return " ".join(parts).lstrip("+ ").strip()

SCORES_META = {
    "MacroScore": {
        "description": "MacroScore composito (Growth, Inflation, Policy, Risk)",
        "formula": _build_score_formula(MACRO_SCORE_WEIGHTS),
        "frequency": "MONTHLY",
    },
}

REGIME_THRESHOLDS = [
    (0.5,           "Espansione"),
    (0.0,           "Ripresa"),
    (-0.5,          "Rallentamento"),
    (float("-inf"), "Recessione"),
]


def _get_regime(score: float | None) -> str:
    if score is None or not math.isfinite(score):
        return "N/A"
    for threshold, label in REGIME_THRESHOLDS:
        if score > threshold:
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

    macro_raw_rows      = _query_macro_raw(db, filter_val)
    macro_proc_rows     = _query_macro_processed(db, filter_val)
    pillar_rows         = _query_pillars(db, filter_val)
    scores_rows         = _query_scores(db, filter_val)
    market_rows         = _query_market(db, filter_val)

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
    return [r for r in rows if f in r["symbol"].upper() or f in r["description"].upper()]


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

    rows = []
    for symbol, meta in MACRO_META.items():
        r = agg.get(symbol)
        rows.append({
            "id": f"macro_raw:{symbol}",
            "symbol": symbol,
            "description": meta.get("description", ""),
            "formula": None,
            "source": r.source if r else "FRED",
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

    rows = []
    for symbol, meta in PROCESSED_META.items():
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

    rows = []
    for pillar, meta in PILLAR_META.items():
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
    REQUIRED_PILLARS = set(MACRO_SCORE_WEIGHTS.keys())

    all_rows = (
        db.query(MacroPillar.date, MacroPillar.pillar)
        .filter(MacroPillar.pillar.in_(REQUIRED_PILLARS))
        .all()
    )

    if not all_rows:
        return _filter_rows([{
            "id": "scores:MacroScore", "symbol": "MacroScore",
            "description": SCORES_META["MacroScore"]["description"],
            "formula": SCORES_META["MacroScore"]["formula"],
            "source": "internal", "frequency": "MONTHLY",
            "first_date": None, "last_date": None, "row_count": 0,
            "data_category": "scores",
        }], filter_val)

    df = pd.DataFrame(all_rows, columns=["date", "pillar"])
    complete_dates = (
        df.groupby("date")["pillar"]
        .apply(set)
        .pipe(lambda s: s[s.apply(lambda p: p == REQUIRED_PILLARS)])
        .index.sort_values()
        .tolist()
    )

    first_date = complete_dates[0] if complete_dates else None
    last_date = complete_dates[-1] if complete_dates else None

    return _filter_rows([{
        "id": "scores:MacroScore",
        "symbol": "MacroScore",
        "description": SCORES_META["MacroScore"]["description"],
        "formula": SCORES_META["MacroScore"]["formula"],
        "source": "internal",
        "frequency": "MONTHLY",
        "first_date": str(first_date) if first_date else None,
        "last_date": str(last_date) if last_date else None,
        "row_count": len(complete_dates),
        "data_category": "scores",
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

    rows = []
    for symbol, meta in MARKET_META.items():
        r = agg.get(symbol)
        rows.append({
            "id": f"market:{symbol}",
            "symbol": symbol,
            "description": meta.get("description", ""),
            "formula": None,
            "source": r.source if r else "YAHOO",
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
        REQUIRED_PILLARS = set(MACRO_SCORE_WEIGHTS.keys())

        q = (
            db.query(MacroPillar.date, MacroPillar.pillar, MacroPillar.score)
            .filter(MacroPillar.pillar.in_(REQUIRED_PILLARS))
        )
        if start_date:
            q = q.filter(MacroPillar.date >= start_date)
        if end_date:
            q = q.filter(MacroPillar.date <= end_date)

        all_rows = q.order_by(MacroPillar.date).all()
        if not all_rows:
            raise HTTPException(status_code=404, detail="Nessun dato disponibile per MacroScore")

        df = pd.DataFrame(all_rows, columns=["date", "pillar", "score"])

        # verifica che ogni data abbia esattamente i pillar richiesti
        complete_mask = (
            df.groupby("date")["pillar"]
            .apply(set)
            .pipe(lambda s: s[s.apply(lambda p: p == REQUIRED_PILLARS)])
            .index
        )
        df = df[df["date"].isin(complete_mask)]

        if df.empty:
            raise HTTPException(status_code=404, detail="Nessuna data con tutti i pillar disponibili")

        # pivot: date × pillar → score, calcola MacroScore e regime
        pivot = df.pivot(index="date", columns="pillar", values="score")
        pivot["MacroScore"] = sum(
            pivot[p] * w for p, w in MACRO_SCORE_WEIGHTS.items()
        )
        pivot["regime"] = pivot["MacroScore"].apply(_get_regime)
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

        return {
            "symbol": "MacroScore",
            "description": "MacroScore composito (Growth, Inflation, Policy, Risk)",
            "source": "internal",
            "frequency": "MONTHLY",
            "first_date": str(dates[0]) if dates else None,
            "last_date": str(dates[-1]) if dates else None,
            "row_count": len(dates),
            "data_category": "scores",
            "points": points,
        }

    # macro processed
    if symbol in PROCESSED_META:
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
            meta = PROCESSED_META[symbol]
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
        meta = MACRO_META.get(symbol, {})
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
        meta = MARKET_META.get(symbol, {})
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
        meta = PILLAR_META.get(symbol, {})
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
