# 📘 Backtest Options — Documento Unificato (Baseline Operativa Completa)

---

## 1. Obiettivo

Costruire un motore di backtest per strategie opzionali su ETF/indici con:

* pricing teorico (Black-Scholes)
* gestione greche
* strutture multi-leg (spread, butterfly)
* simulazione IV
* integrazione macro regime
* persistenza completa (snapshot + performance)
* analytics e visualizzazione
* evoluzione verso motore adattivo

---

## 2. Architettura

### Layer

1. **Domain (runtime)**

   * `OptionLeg`
   * `Position`
   * `Portfolio`

2. **Persistence**

   * `BacktestRun`
   * `BacktestPosition`
   * `BacktestPositionSnapshot`
   * `BacktestPortfolioPerformance`
   * `BacktestPerformance`
   * `BacktestRunParameter`

3. **Engine**

   * loop giornaliero
   * update mercato
   * entry/exit
   * salvataggio snapshot

4. **Data preparation**

   * costruzione dataset (prezzi + IV + macro)

---

## 3. Flusso del backtest

Per ogni giorno:

1. update posizioni (S, IV, tempo)
2. snapshot posizioni
3. close logic
4. entry logic (strategy selection)
5. snapshot portfolio
6. salvataggio NAV e return

---

## 4. Simulazione IV

### Formula

$$
IV_t = \operatorname{clamp}\left(
1.15 \cdot \sqrt{252} \cdot \operatorname{std}(r_{t-19:t})

* \alpha \cdot \max(0, -r_t),
  ; iv_{\min}, ; iv_{\max}
  \right)
  $$

### Implementazione

```python
def enrich_with_iv(df, alpha=4.0, iv_min=0.10, iv_max=0.80):
    df = df.sort_values("date").copy()

    log_ret = np.log(df["close"] / df["close"].shift(1))
    rv_20 = log_ret.rolling(20).std()

    downside_boost = alpha * (-log_ret).clip(lower=0)
    iv = 1.15 * np.sqrt(252) * rv_20 + downside_boost

    df["iv"] = iv.clip(lower=iv_min, upper=iv_max)
    return df
```

### Note

* warmup necessario (~40–60 giorni)
* eseguita prima del backtest
* aggiunge solo la colonna `iv`

---

## 5. P&L Model

### Definizioni

* **Realized PnL** → posizioni chiuse
* **Unrealized PnL** → posizioni aperte
* **Total PnL** → somma

### Portfolio

```python
_realized_pnl: float = field(init=False)

def __post_init__(self):
    self.cash = self.initial_cash
    self._realized_pnl = 0.0

@property
def realized_pnl(self):
    return self._realized_pnl

@property
def unrealized_pnl(self):
    return sum(p.pnl for p in self.positions if p.is_open)

@property
def total_pnl(self):
    return self.realized_pnl + self.unrealized_pnl
```

---

## 6. Performance Tracking

### BacktestPerformance

* `nav`
* `period_return`

```python
period_return = (nav_t / nav_{t-1}) - 1
```

### BacktestRun (metriche aggregate)

* CAGR
* Volatility
* Sharpe
* Max Drawdown
* Win Rate
* Profit Factor
* N trades

---

## 7. Strategy Engine

### StrategySpec

```python
@dataclass
class StrategySpec:
    name: str
    builder: Optional[Callable[..., Position]]
    should_trade: bool = True
```

---

### Strategie implementate

* bull_put_spread
* bear_call_spread
* put_broken_wing_butterfly (neutral)

---

### Esempio builder

```python
def create_bear_call_spread(...):
    short_strike = S * 1.05
    long_strike = S * 1.08
```

---

### Strategy Selection

```python
def select_strategy(iv, macro_regime):
    if macro_regime == "RISK_ON" and iv < 0.25:
        return bull_put_strategy()
    if macro_regime == "RISK_OFF" and iv > 0.30:
        return bear_call_strategy()
    return neutral_broken_wing_strategy()
```

---

## 8. Macro Integration

### Funzione

```python
def compute_macro_risk_score(db, date):
```

### Logica

* expansion → +1
* neutral → 0
* contraction → -1

### Classificazione

* ≥ 0.5 → RISK_ON
* ≤ -0.5 → RISK_OFF
* else → NEUTRAL

### Uso

```python
_, macro_regime = compute_macro_risk_score(db, date)
strategy = select_strategy(iv, macro_regime)
```

---

## 9. Parametrizzazione

### Entity

```python
BacktestRunParameter:
- key
- value (string)
- unit
```

### Mapping

```python
params_dict = {
    p.key: {"value": p.value, "unit": p.unit}
}
```

---

## 10. Warmup Period

```python
load_start = run.start_date - timedelta(days=40)
df = df[df["date"] >= run.start_date]
```

---

## 11. Analytics API

### Lista posizioni

```
GET /runs/{run_id}/positions
```

Include:

* metadata
* realized_pnl
* performance_pct
* days_in_trade
* latest snapshot (opzionale)

---

### History posizione

```
GET /runs/{run_id}/positions/{position_id}/history
```

Include:

* header posizione
* serie temporale snapshot

---

## 12. Visualizzazione

### Layout

```
[ underlying vs position ]
[ pnl vs iv             ]
```

### Grafico 1

* underlying_price
* position_price

### Grafico 2

* position_pnl
* iv

### Caratteristiche

* asse X condiviso
* doppio asse Y
* sincronizzazione

---

## 13. Stato attuale

Sistema supporta:

* IV realistica
* PnL completo
* multi-strategy engine
* macro integration
* tracking storico
* base analytics

---

## 14. Estensioni future

### 14.1 Entry Logic avanzata

Problema:

* oggi basata solo su macro + IV

Evoluzione:

* indicatori tecnici (RSI, MACD)
* trend detection
* IV rank / percentile
* multi-factor decision

---

### 14.2 Exit Logic avanzata

Evoluzione:

* stop loss dinamico
* trailing profit
* exit su inversione segnali
* gestione greche
* adattamento IV

---

### 14.3 Commissioni e Slippage

Da introdurre:

* costo per contratto
* bid/ask spread
* slippage dinamico

---

### 14.4 Indicatori tecnici

Possibili:

* RSI
* MACD
* Moving averages
* ATR
* Bollinger Bands

Uso:

* filtro entry
* timing
* conferma segnali

---

### 14.5 Motore adattivo / predittivo

Evoluzione verso:

1. rule-based avanzato
2. regime detection
3. machine learning
4. reinforcement learning

---

## 15. Priorità evolutive

1. migliorare entry logic
2. migliorare exit logic
3. introdurre costi
4. integrare indicatori tecnici
5. costruire motore adattivo

---

## 16. Stato maturità

Sistema evoluto da:

* prototipo statico

a:

* motore di backtest **dinamico, multi-strategy, macro-aware, estendibile**


# 📊 Backtest UI — Prossimi Step (Interattività e Analisi)

---

## 1. Interattività grafici

Obiettivo: rendere i grafici realmente utilizzabili per analisi.

### Da implementare
- hover sincronizzato tra i due grafici
- tooltip condiviso con:
  - date
  - underlying_price
  - position_price
  - position_pnl
  - iv
- linea verticale comune (crosshair)
- zoom orizzontale
- brush temporale (selezione range)
- legenda cliccabile (toggle serie)

---

## 2. Annotazioni evento posizione

Aggiungere marker sul grafico:

- apertura posizione
- chiusura posizione
- cambio regime macro
- cambio strategia (futuro)
- eventuale motivo uscita

👉 fondamentale per interpretabilità

---

## 3. Pannello dettaglio posizione

Visualizzare contesto sopra o accanto ai grafici:

- strategy type
- status (OPEN / CLOSED)
- opened_at / closed_at
- entry_underlying
- entry_iv
- entry_macro_regime
- initial_value
- close_value
- realized_pnl
- days_in_trade

---

## 4. Gestione stati frontend

Gestire correttamente:

- loading state
- empty state
- errore API
- posizione aperta vs chiusa
- dati mancanti

---

## 5. Performance frontend

Per dataset grandi:

- memoization
- evitare rerender inutili
- lazy loading history (solo on click)
- normalizzazione dati

---

## 6. Tabella posizioni integrata

Funzionalità:

- click su riga → carica grafico posizione
- evidenziazione posizione selezionata
- filtri:
  - OPEN / CLOSED
  - strategy type
  - macro regime
- sorting:
  - pnl
  - durata
  - data apertura

---

## 7. Analisi avanzata (step successivo)

Opzionale:

- terzo grafico:
  - delta
  - gamma
  - theta
  - vega
- toggle “advanced view”

---

## 8. Realismo economico

Da introdurre dopo UI stabile:

- commissioni
- slippage

👉 impatta direttamente i grafici PnL

---

## 📌 Ordine di implementazione consigliato

1. tooltip sincronizzato  
2. marker apertura/chiusura  
3. zoom + brush  
4. click tabella → dettaglio posizione  
5. filtri lista posizioni  
6. pannello metadati  
7. commissioni/slippage  
8. greche opzionali  

---

## 🎯 Obiettivo

Passare da:

- visualizzazione statica

a:

- **strumento interattivo di analisi trading**
