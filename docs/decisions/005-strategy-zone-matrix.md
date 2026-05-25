# ADR 005 — Strategy Selection Matrix per Zone di Mercato

**Data**: 2026-05-10
**Status**: attivo

## Contesto

Il Decision Engine L2 (`strategy_selector.py`) classifica il mercato in 4 zone
tramite `classify_zone()` e poi seleziona una strategia tramite `select_strategy()`.

Quando una zona ha più candidati (es. Zone B UP → [BPS, Jade Lizard]), la funzione
`rank_strategies()` restituiva sempre `candidates[0]()` indipendentemente dalle
condizioni di mercato. Alcune strategie erano quindi dead code strutturale — mai
raggiungibili indipendentemente dai dati.

Problema aggiuntivo: in un backtest 2015-2024 su SPY, Zone B e Zone D non producevano
mai posizioni aperte per via del scoring (vedi sezione "Limitazioni note").

## Classificazione Zone

```
                  │  IV Rank < 30      │  IV Rank ≥ 30
──────────────────┼────────────────────┼───────────────────
ADX ≥ 25 (trend)  │  ZONE A            │  ZONE B
ADX < 25 (lateral)│  ZONE C            │  ZONE D
```

Soglie: `iv_rank_threshold = 30`, `adx_threshold = 25`.

## Decisione — Mappa Strategia × Zona

### Zone A — Trend + Low IV
Setup: IV economica + trend direzionale → acquistare premium con bias direzionale.
Logica: comprare quando le opzioni costano poco.

| Condizione (trend_signal) | Strategia | Candidati |
|---|---|---|
| UP (1) | Bull Call Spread | unico |
| DOWN (-1) | Bear Put Spread | unico |
| NEUTRAL (0) | Put BWB | unico |

Nessun ranking necessario — un candidato per condizione.

---

### Zone B — Trend + High IV
Setup: IV cara + trend direzionale → vendere premium con bias direzionale.
Logica: raccogliere theta, la direzione protegge il lato scoperto.

| Condizione | Strategia primaria | Strategia alternativa | Criterio di selezione |
|---|---|---|---|
| UP (1) | Bull Put Spread | Jade Lizard | se iv_rank > 50 → JL (più premium, più aggressivo) |
| DOWN (-1) | Bear Call Spread | Reverse Jade Lizard | se iv_rank > 50 → RJL |
| NEUTRAL (0) | no_trade | — | trend senza direzione = nessun edge direzionale |

**Jade Lizard**: aggiunge una call scoperta a un BPS. Adatta quando IV è molto
alta e ci si aspetta un cap naturale al rialzo.
**Reverse Jade Lizard**: speculare — put scoperta aggiunta a un BCS.

---

### Zone C — Lateral + Low IV
Setup: mercato compresso (squeeze) → aspettare esplosione di volatilità.
Logica: comprare straddle/strangle quando IV è depressa, aspettare breakout.

| Condizione (squeeze_intensity) | Strategia | Candidati |
|---|---|---|
| > 70 | Long Straddle | unico |
| > 50 | Long Strangle | unico |
| ≤ 50 | Put BWB | unico |

Nessun ranking necessario.

---

### Zone D — Lateral + High IV
Setup: IV cara + mercato fermo → vol crush.
Logica: incassare premium su ambo i lati, il mercato non si muove abbastanza.

| Condizione (iv_rank) | Strategia primaria | Strategia alternativa | Criterio di selezione |
|---|---|---|---|
| > 65 | Iron Butterfly | — | unico, range stretto, massimo theta |
| 50–65 | Iron Condor | Calendar Spread | se adx < 15 → Calendar (mercato ultra-laterale con struttura a termine) |
| 30–50 | Jade Lizard | Diagonal Spread | se abs(trend_signal) > 0 → Diagonal (leggera direzionalità) |

**Calendar Spread**: sfrutta il differenziale di theta tra scadenze diverse.
Preferito a IC quando ADX è molto basso (< 15), indicando assenza totale di trend.
**Diagonal Spread**: come Calendar ma con strike diversi. Adatto quando c'è una
leggera componente direzionale anche in regime laterale.

---

## Strategie recuperate dal dead code

| Strategia | Stato precedente | Condizione di attivazione |
|---|---|---|
| Jade Lizard (Zone B UP) | Sempre secondo → mai selezionato | iv_rank > 50 in Zone B UP |
| Reverse Jade Lizard (Zone B DOWN) | Sempre secondo → mai selezionato | iv_rank > 50 in Zone B DOWN |
| Calendar Spread | Sempre secondo → mai selezionato | adx < 15 in Zone D, iv_rank 50–65 |
| Diagonal Spread | Sempre secondo → mai selezionato | trend_signal ≠ 0 in Zone D, iv_rank 30–50 |

---

## Limitazioni note

**Zone B — scoring strutturalmente basso**
In mercati trending con IV alta, la RV tende ad essere alta quanto la IV.
L'edge sintetico `abs(fair_value) * max(0, (IV-RV)/IV)` → 0.
Il `pricing_edge_score` (peso 35%) crolla → composite score raramente supera 75.
Soluzione futura: calibrare threshold_open per zona, non uno solo globale.

**Zone D — risk_reward_score penalizza strutture multi-leg**
Iron Condor e Iron Butterfly hanno 4 strike. Il calcolo attuale usa
`spread_width = max(strikes) - min(strikes)` → massima distanza tra strike estremi.
Per un condor con wing spread di 10 punti su ogni lato, spread_width = 20.
Il `max_loss` risultante è sovrastimato → `rr_ratio` ≈ 0 → `risk_reward_score` = 0.
Richiede un calcolo specifico per strutture multi-leg (ADR separato).

---

## Implementazione

La mappa è implementata interamente in `backend/app/engines/option/strategy_selector.py`:
- `STRATEGY_MATRIX`: dizionario zona → condizione → lista candidati
- `select_strategy()`: routing per zona e sotto-condizione
- `rank_strategies()`: criterio di selezione tra candidati multipli

I criteri di ranking usano solo variabili già disponibili nel pipeline:
`iv_rank`, `adx`, `trend_signal` — nessun dato aggiuntivo richiesto.
