from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
import math
from app.db.session import SessionLocal
from app.db.macro_raw import MacroRaw
from app.db.macro_pillar import MacroPillar
from app.db.market_price import MarketPrice

router = APIRouter(tags=["data"])

MACRO_META = {
    "CUMFNS":         {"description": "Capacity Utilization: Manufacturing",       "frequency": "MONTHLY"},
    "GDPC1":          {"description": "Real Gross Domestic Product",               "frequency": "QUARTERLY"},
    "GDPC1_YOY":      {"description": "Real GDP YoY",                              "frequency": "QUARTERLY"},
    "INDPRO":         {"description": "Industrial Production Index",               "frequency": "MONTHLY"},
    "INDPRO_YOY":     {"description": "Industrial Production YoY",                 "frequency": "MONTHLY"},
    "CPIAUCSL":       {"description": "Consumer Price Index (All Urban)",           "frequency": "MONTHLY"},
    "CPI_YOY":        {"description": "CPI YoY",                                   "frequency": "MONTHLY"},
    "PPIFIS":         {"description": "Producer Price Index",                      "frequency": "MONTHLY"},
    "PPI_YOY":        {"description": "PPI YoY",                                   "frequency": "MONTHLY"},
    "T5YIE":          {"description": "5-Year Breakeven Inflation Rate",           "frequency": "DAILY"},
    "FEDFUNDS":       {"description": "Federal Funds Effective Rate",              "frequency": "MONTHLY"},
    "FEDFUNDS_DELTA": {"description": "Fed Funds Rate — variazione mensile",       "frequency": "MONTHLY"},
    "T10Y2Y":         {"description": "10-Year Treasury Minus 2-Year Treasury",    "frequency": "DAILY"},
    "VIXCLS":         {"description": "CBOE Volatility Index (VIX)",               "frequency": "DAILY"},
    "BAA10Y":         {"description": "Moody's Baa Corporate Bond Spread",         "frequency": "DAILY"},
    "NFCI":           {"description": "Chicago Fed National Financial Conditions", "frequency": "WEEKLY"},
}

MARKET_META = {
    "SPY": {"description": "S&P 500 ETF (Equity)",                           "frequency": "DAILY"},
    "IEF": {"description": "iShares 7-10 Year Treasury Bond ETF (Bond)",     "frequency": "DAILY"},
    "DBC": {"description": "Invesco DB Commodity Index Tracking Fund",       "frequency": "DAILY"},
    "BIL": {"description": "SPDR Bloomberg 1-3 Month T-Bill ETF (Cash)",     "frequency": "DAILY"},
}

PILLAR_META = {
    "Growth":    {"description": "Forza del ciclo economico reale",          "frequency": "MONTHLY"},
    "Inflation": {"description": "Pressione inflattiva realizzata e attesa", "frequency": "MONTHLY"},
    "Policy":    {"description": "Stance della banca centrale (Fed)",        "frequency": "MONTHLY"},
    "Risk":      {"description": "Stress finanziario e risk aversion",       "frequency": "MONTHLY"},
}


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

    raw_rows = _query_raw(db, filter_val)
    pillar_rows = _query_pillars(db, filter_val)

    if data_category == "pillars":
        if orderBy == "symbol":
            pillar_rows.sort(key=lambda r: r["symbol"])
        items = _paginate(pillar_rows, page, limit)
        active_category = "pillars"
    else:
        if orderBy == "symbol":
            raw_rows.sort(key=lambda r: r["symbol"])
        items = _paginate(raw_rows, page, limit)
        active_category = "raw"

    return {
        "items": items,
        "active_category": active_category,
        "counters": {"raw": len(raw_rows), "pillars": len(pillar_rows)},
    }


def _query_raw(db: Session, filter_val: str | None) -> list[dict]:
    macro = (
        db.query(
            MacroRaw.indicator.label("symbol"),
            MacroRaw.source,
            func.min(MacroRaw.date).label("first_date"),
            func.max(MacroRaw.date).label("last_date"),
            func.count(MacroRaw.date).label("row_count"),
        )
        .group_by(MacroRaw.indicator, MacroRaw.source)
        .all()
    )

    market = (
        db.query(
            MarketPrice.symbol,
            MarketPrice.source,
            func.min(MarketPrice.date).label("first_date"),
            func.max(MarketPrice.date).label("last_date"),
            func.count(MarketPrice.date).label("row_count"),
        )
        .group_by(MarketPrice.symbol, MarketPrice.source)
        .all()
    )

    rows = []
    for r in macro:
        meta = MACRO_META.get(r.symbol, {})
        rows.append({
            "id": f"macro:{r.symbol}",
            "symbol": r.symbol,
            "description": meta.get("description", ""),
            "source": r.source,
            "frequency": meta.get("frequency", ""),
            "first_date": str(r.first_date) if r.first_date else None,
            "last_date": str(r.last_date) if r.last_date else None,
            "row_count": r.row_count,
            "data_category": "raw",
        })

    for r in market:
        meta = MARKET_META.get(r.symbol, {})
        rows.append({
            "id": f"market:{r.symbol}",
            "symbol": r.symbol,
            "description": meta.get("description", ""),
            "source": r.source,
            "frequency": meta.get("frequency", ""),
            "first_date": str(r.first_date) if r.first_date else None,
            "last_date": str(r.last_date) if r.last_date else None,
            "row_count": r.row_count,
            "data_category": "raw",
        })

    if filter_val:
        f = filter_val.upper()
        rows = [r for r in rows if f in r["symbol"].upper() or f in r["description"].upper()]

    return rows


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
            "source": "internal",
            "frequency": meta["frequency"],
            "first_date": str(r.first_date) if r and r.first_date else None,
            "last_date": str(r.last_date) if r and r.last_date else None,
            "row_count": r.row_count if r else 0,
            "data_category": "pillar",
        })

    if filter_val:
        f = filter_val.upper()
        rows = [r for r in rows if f in r["symbol"].upper() or f in r["description"].upper()]

    return rows



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
            "data_category": "raw",
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
            "data_category": "raw",
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
