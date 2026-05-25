# ADR 004 — Edge sintetico IV/RV in backtest vs edge reale in live trading

**Data**: 2026-05-08
**Status**: attivo

## Contesto

Il composite_score del Decision Engine (L4) include una dimensione `pricing_edge_score`
con peso del 35%. In live trading, l'edge è calcolato come:

```
edge = fair_value - market_price
```

dove `market_price` è il mid del bid/ask reale. In backtest non esiste un feed di
prezzi di mercato reali per le opzioni, quindi `market_price` cade sul fallback
`fair_value`, rendendo `edge = 0` per ogni trade. Il 35% del composite_score
è sempre 0 → il punteggio non supera mai 65 → il Decision Engine non restituisce
mai `OPEN` (threshold = 75).

## Decisione

In assenza di `market_price` reale (backtest mode), calcolare un **edge sintetico**
basato sul premio IV rispetto alla realized volatility:

```
edge = fair_value * max(0, (IV - RV) / IV)
```

**Logica**: la strategia del sistema è vendere premium quando le opzioni sono
statisticamente care (IV > RV). L'edge sintetico quantifica questa "carezza" teorica
proporzionalmente al valore della posizione.

Il campo `edge_source` nel `DecisionLog` traccia quale formula è stata usata:
- `"market_price"` → edge reale da feed (live trading)
- `"synthetic_iv_rv"` → edge sintetico IV/RV (backtest mode)

## Come usare edge_source quando arriva il feed reale

1. Filtrare i decision_logs per `edge_source = "market_price"` per analisi live
2. Confrontare i composite_score tra le due serie per stimare il bias del backtest
3. Ricalibrate `threshold_open` (attualmente 75) per allineare i due contesti
4. Quando il feed è stabile, deprecare la logica sintetica

## Trade-off accettati

- L'edge sintetico è un indicatore di regime (cambia lentamente), non di qualità
  esecutiva del singolo trade. Può sovrastimare o sottostimare l'edge reale.
- I composite_score del backtest non sono direttamente comparabili con quelli
  live per la dimensione pricing_edge. Le altre 4 dimensioni (R/R, breakeven,
  execution cost, capital efficiency) sono identiche.
- La calibrazione di `threshold_open` sui dati backtest è valida solo per
  `edge_source = "synthetic_iv_rv"`.

## Alternative scartate

- **Abbassare il threshold a 50 per backtest**: semplice ma disallinea i parametri
  tra backtest e live — ottimizzeresti su criteri diversi da quelli reali.
- **Ridistribuire i pesi escludendo edge in backtest**: formula diversa tra i due
  contesti → composite_score non comparabile, più complesso da mantenere.
