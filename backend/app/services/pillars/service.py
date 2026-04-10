from sqlalchemy import extract
from sqlalchemy.orm import Session
from app.db.macro_processed import MacroProcessed
from app.db.macro_regimes import MacroRegime
from app.services.config_repo import get_pillars
from app.core.regime_config import (
    REGIME_THRESHOLD_UP, REGIME_THRESHOLD_DOWN,
    REGIME_HYSTERESIS, REGIME_CONFIRM_MONTHS,
    REGIME_EXTREME,
)
import logging

logger = logging.getLogger(__name__)

def _raw_regime(score: float) -> str:
  if score >= REGIME_THRESHOLD_UP:
    return "expansion"
  if score <= REGIME_THRESHOLD_DOWN:
    return "contraction"
  return "neutral"

def _next_regime(
    score: float,
    current_regime: str,
    counter: int,
    pending: str | None,
) -> tuple[str, int, str | None]:
  """
  Restituisce (new_regime, new_counter, new_pending).
  """
  # segnale estremo: transizione immediata
  if score >= REGIME_EXTREME:
      return "expansion", 0, None
  if score <= -REGIME_EXTREME:
      return "contraction", 0, None

  # regime suggerito dallo score con isteresi
  if current_regime == "expansion":
    if score < (REGIME_THRESHOLD_UP - REGIME_HYSTERESIS):
      raw = "neutral" if score > REGIME_THRESHOLD_DOWN else "contraction"
    else:
      raw = "expansion"
  elif current_regime == "contraction":
    if score > (REGIME_THRESHOLD_DOWN + REGIME_HYSTERESIS):
      raw = "neutral" if score < REGIME_THRESHOLD_UP else "expansion"
    else:
      raw = "contraction"
  else:  # neutral
    raw = _raw_regime(score)

  # segnale coerente col regime attuale
  if raw == current_regime:
    return current_regime, 0, None

  # accumulo conferma
  if raw == pending:
    new_counter = counter + 1
    if new_counter >= REGIME_CONFIRM_MONTHS:
      return raw, 0, None
    return current_regime, new_counter, pending

  # primo mese verso un nuovo regime
  return current_regime, 1, raw

def compute_pillars(
    db: Session,
    pillar: str | None = None,
    start_date=None,
    end_date=None,
):
  logger.info(f"*** compute pillars *** pillar={pillar or 'all'}")
  pillars = get_pillars(db)

  if pillar:
    if pillar not in pillars:
      raise ValueError(f"Pillar '{pillar}' non trovato")
    pillars = {pillar: pillars[pillar]}

  q = db.query(MacroProcessed.date).distinct()
  if start_date:
    q = q.filter(MacroProcessed.date >= start_date)
  if end_date:
    q = q.filter(MacroProcessed.date <= end_date)
  dates = [d[0] for d in q.order_by(MacroProcessed.date).all()]

  # stato precedente per ogni pillar: (regime, counter, pending)
  # in full rebuild partiamo da zero; in incrementale carichiamo l'ultimo record
  prev_state: dict[str, dict] = {}
  is_full = start_date is None and end_date is None

  if not is_full:
    # modalità incrementale: carica l'ultimo stato disponibile prima di start_date
    lookup_date = start_date or dates[0] if dates else None
    for p in pillars:
      last = (
        db.query(MacroRegime)
          .filter(MacroRegime.pillar == p)
          .filter(MacroRegime.date < lookup_date)
          .order_by(MacroRegime.date.desc())
          .first()
      )
      if last:
        prev_state[p] = {
            "regime":  last.regime,
            "counter": last.counter,
            "pending": last.pending,
        }
      else:
        prev_state[p] = {"regime": "neutral", "counter": 0, "pending": None}
  else:
    for p in pillars:
      prev_state[p] = {"regime": "neutral", "counter": 0, "pending": None}

  for date in dates:
    for p, indicators in pillars.items():
      rows = (
        db.query(MacroProcessed.z_score_ema, MacroProcessed.indicator)
        .filter(MacroProcessed.date == date)
        .filter(MacroProcessed.indicator.in_([ind for ind, _ in indicators]))
        .filter(MacroProcessed.z_score_ema.isnot(None))
        .all()
      )

      if len(rows) != len(indicators):
        continue  # pillar incompleto → skip

      # aggrega z_score_ema con inversione semantica → score del pillar
      invert_map = {ind: inv for ind, inv in indicators}
      score = float(sum(
        (-r.z_score_ema if invert_map[r.indicator] else r.z_score_ema)
        for r in rows
      ) / len(rows))

      # regime detection (score è già EMA-smoothed per indicatore)
      prev = prev_state[p]
      new_regime, new_counter, new_pending = _next_regime(
        score,
        prev["regime"],
        prev["counter"],
        prev["pending"],
      )

      db.merge(MacroRegime(
        date=date,
        pillar=p,
        score=score,
        score_ema=score,  # EMA già applicata per indicatore in process_indicator
        regime=new_regime,
        counter=new_counter,
        pending=new_pending,
      ))

      prev_state[p] = {
        "regime":  new_regime,
        "counter": new_counter,
        "pending": new_pending,
      }

  db.commit()


REGIME_SCORE = {"expansion": 1.0, "neutral": 0.0, "contraction": -1.0}


def compute_macro_risk_score(db: Session, date) -> tuple[float, str]:
    """
    Aggrega i regimi dei 4 pillar in un punteggio tra -1 e 1.
    expansion=+1, neutral=0, contraction=-1 → media semplice.
    score >= 0.5  → RISK_ON
    score <= -0.5 → RISK_OFF
    altrimenti    → NEUTRAL

    Il confronto è per mese: qualunque giorno di maggio 2026 restituisce
    il regime di maggio 2026.
    """
    regimes = (
        db.query(MacroRegime)
        .filter(extract("year", MacroRegime.date) == date.year)
        .filter(extract("month", MacroRegime.date) == date.month)
        .all()
    )
    if not regimes:
        return 0.0, "NEUTRAL"

    score = sum(REGIME_SCORE.get(r.regime, 0.0) for r in regimes) / len(regimes)

    if score >= 0.5:
        label = "RISK_ON"
    elif score <= -0.5:
        label = "RISK_OFF"
    else:
        label = "NEUTRAL"

    return score, label