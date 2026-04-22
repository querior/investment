# Entry Scoring — Quality-Based Sizing

Documento tecnico: implementazione dello score composito di entry secondo il framework.

## Framework Base

**Fonte**: Options Engine Framework, sezione 5 (segnali di ingresso)

Lo score composito valuta la **qualità della posizione** sulla base di sei fattori, ognuno con peso diverso:

```
Q_entry = w1*(100 - IV_rank)       # peso 30% — regime IV
        + w2*(1 - IV/HV_ratio)     # peso 20% — IV vs realized volatility
        + w3*squeeze_intensity     # peso 20% — compressione Bollinger Bands
        + w4*RSI_neutrality        # peso 15% — momentum condition
        + w5*DTE_score             # peso 10% — timing
        + w6*volume_ratio          # peso  5% — liquidity

Score: 0-100
```

---

## Componenti dello Score

### 1. IV Rank (w1 = 30%)

**Logica**: IV bassa = setup migliore (comprare volatilità a prezzo scontato)

```
component_1 = 100 - IV_rank
```

- IV Rank < 30% (bassa) → component_1 > 70 (buono)
- IV Rank > 50% (alta) → component_1 < 50 (cattivo)

**Razionale**: In regime di IV bassa (squeeze), l'entry ha edge migliore perché gli option premium sono sottovalutati.

---

### 2. IV/HV Ratio (w2 = 20%)

**Logica**: IV < HV = buon deal (implied vol below realized vol)

```
component_2 = clamp(100 * (1 - IV/HV_ratio + 1) / 2, 0, 100)
```

- Ratio < 1.0 (IV cheap) → score alto
- Ratio > 1.0 (IV expensive) → score basso

**Razionale**: Quando IV è scambiato con sconto rispetto alla volatilità storica, l'edge statistico è migliore.

---

### 3. Squeeze Intensity (w3 = 20%)

**Logica**: Squeeze = setup di breakout, volatilità sta per esplodere

```
component_3 = squeeze_intensity  (già 0-100 dalla pipeline)
```

**Interpretazione**:
- squeeze_intensity = percentile della larghezza BB nella rolling window
- squeeze_active = true quando BB Width < 20° percentile AND MACD piatto

**Razionale**: Volatilità compressa indica accumulo di energia. Entry è ideale prima del movimento.

---

### 4. RSI Neutrality (w4 = 15%)

**Logica**: RSI intorno a 50 = migliore (nessun bias direzionale)

```
distance = |RSI - 50|
component_4 = max(0, 100 - (distance / 50) * 100)
```

- RSI 50 → score 100 (neutrale perfetto)
- RSI 30/70 → score ~30 (estremo)
- RSI < 20 / > 80 → score 0 (molto estremo)

**Razionale**: Momentum estremo spesso precede reversali. Entry è più pulito con RSI neutrale.

---

### 5. DTE Score (w5 = 10%)

**Logica**: DTE ottimale 35-45 giorni (theta decay + gamma acceleration)

```
Ideal: 35-45 DTE → score 100
Warning: 21-34 o 46-55 DTE → score decrescente
Out of range: < 21 o > 55 DTE → score basso
```

**Nota**: Attualmente il builder crea sempre posizioni a 45 DTE (fisso). Questo score è informativo per future ottimizzazioni (DTE adattivo).

---

### 6. Volume Ratio (w6 = 5%)

**Logica**: Volume compression (ratio 0.7-1.0) = setup, expansion (> 1.5) = noise

```
ratio 0.5-1.0: score da 50 a 100
ratio 1.0-1.5: score da 100 a 50
ratio < 0.5 o > 1.5: score basso (30)
```

**Razionale**: Basso volume relativo indica accumulo (squeeze), alto volume indica instabilità.

---

## Soglie di Sizing

Una volta calcolato lo score, si determina la **position size**:

```python
Score > 75: size multiplier = 100% (full size)
Score 60-74: size multiplier = 75% (3/4 size)
Score < 60: size multiplier = 0% (no entry)
```

Interpolazione lineare tra 60 e 75.

### Esempio

```
Entry score = 72 → (72 - 60) / (75 - 60) × (1.0 - 0.75) + 0.75 = 80% size
```

---

## Parametri Tunable

Tutti gli score component e i threshold sono configurabili via `BacktestRunParameter`:

| Parametro | Default | Descrizione |
|-----------|---------|-------------|
| `entry_score.w1_iv_rank` | 0.30 | Peso IV Rank |
| `entry_score.w2_iv_hv` | 0.20 | Peso IV/HV Ratio |
| `entry_score.w3_squeeze` | 0.20 | Peso Squeeze Intensity |
| `entry_score.w4_rsi` | 0.15 | Peso RSI Neutrality |
| `entry_score.w5_dte` | 0.10 | Peso DTE Score |
| `entry_score.w6_volume` | 0.05 | Peso Volume Ratio |
| `entry_score.dte_min` | 21 | DTE minimo (giorni) |
| `entry_score.dte_optimal_min` | 35 | DTE inizio range ottimale |
| `entry_score.dte_optimal_max` | 45 | DTE fine range ottimale |
| `entry_score.dte_max` | 55 | DTE massimo |
| `entry_size.threshold_full` | 75 | Score min per full size |
| `entry_size.threshold_reduced` | 60 | Score min per reduced size |
| `entry_size.multiplier_full` | 1.0 | Size multiplier per score > 75 |
| `entry_size.multiplier_reduced` | 0.75 | Size multiplier per score 60-74 |

---

## Implementazione

**File**: `backend/app/backtest/domain/strategy/entry_scoring.py`

### Funzioni

```python
def calculate_entry_score(row: pd.Series, entry_config: dict) -> float:
    """Ritorna score 0-100"""

def calculate_position_size(entry_score: float, size_config: dict) -> float:
    """Ritorna multiplier 0.0-1.0"""
```

### Flusso di Esecuzione

1. `select_strategy(row, entry_config)` chiama `calculate_entry_score()`
2. Computa il multiplier con `calculate_position_size()`
3. Aggiunge il multiplier a `StrategySpec`
4. In `run_eod_backtest()`, la position viene scalata da `_scale_position(position, multiplier)`

---

## Esempio: Backtest Run

### Setup
```python
entry_config = {
    "entry_score.w1_iv_rank": 0.30,
    "entry_score.w2_iv_hv": 0.20,
    "entry_score.w3_squeeze": 0.20,
    "entry_score.w4_rsi": 0.15,
    "entry_score.w5_dte": 0.10,
    "entry_score.w6_volume": 0.05,
    "entry_size.threshold_full": 75,
    "entry_size.threshold_reduced": 60,
}
```

### Scenario 1: Squeeze Setup Perfetto

```
Row data:
  iv_rank = 15% (bassa) → component_1 = 85
  iv_rv_ratio = 0.85 (cheap) → component_2 = 75
  squeeze_intensity = 95 (compressa) → component_3 = 95
  rsi_14 = 48 (neutrale) → component_4 = 96
  volume_ratio = 0.75 (contrazione) → component_6 = 75

Score = 0.30*85 + 0.20*75 + 0.20*95 + 0.15*96 + 0.10*100 + 0.05*75
      = 25.5 + 15 + 19 + 14.4 + 10 + 3.75
      = 87.65 → 88

Size multiplier = 100% (score > 75)
→ Open FULL size position
```

### Scenario 2: Setup Mediocre

```
Row data:
  iv_rank = 45% (neutrale) → component_1 = 55
  iv_rv_ratio = 1.05 (expensive) → component_2 = 48
  squeeze_intensity = 50 (niente squeeze) → component_3 = 50
  rsi_14 = 65 (overbought) → component_4 = 70
  volume_ratio = 1.2 (expansion) → component_6 = 50

Score = 0.30*55 + 0.20*48 + 0.20*50 + 0.15*70 + 0.10*100 + 0.05*50
      = 16.5 + 9.6 + 10 + 10.5 + 10 + 2.5
      = 59

Size multiplier = 0% (score < 60)
→ NO ENTRY
```

### Scenario 3: Setup Buono ma Non Ideale

```
Row data:
  iv_rank = 25% (bassa) → component_1 = 75
  iv_rv_ratio = 0.95 (buono) → component_2 = 52
  squeeze_intensity = 70 (moderata) → component_3 = 70
  rsi_14 = 52 (quasi neutrale) → component_4 = 96
  volume_ratio = 0.85 (contrazione lieve) → component_6 = 68

Score = 0.30*75 + 0.20*52 + 0.20*70 + 0.15*96 + 0.10*100 + 0.05*68
      = 22.5 + 10.4 + 14 + 14.4 + 10 + 3.4
      = 74.7 → 75

Size multiplier = (75 - 60) / (75 - 60) × (1.0 - 0.75) + 0.75 = 100%
→ FULL SIZE (marginal ma sopra threshold)

Oppure se score fosse 71:
Size multiplier = (71 - 60) / (75 - 60) × 0.25 + 0.75 = 73.3% → ~75% size
```

---

## Validazione e Tuning

### Best Practices

1. **Non modificare i pesi** della formula di default senza backtesting approfondito
2. **Inizia conservatore**: threshold_full = 75 è appropriato
3. **Monitora la distribuzione degli score**: qual % di entry sono full/reduced/skip?
4. **Correla score con P&L**: entry ad alto score hanno P&L migliore?

### Calibrazione

Se il backtest mostra:
- **P&L peggiore** → aumenta i threshold (es. threshold_full = 80)
- **Troppi skip** → diminuisci i threshold (es. threshold_reduced = 55)
- **Troppo rumore** → aumenta il peso w1 (IV Rank è il filtro più potente)

---

## Futuri Miglioramenti

1. **Volatility term structure** — entry score basato su skew/smile della IV
2. **Regime-aware weights** — pesi diversi per zona (A/B/C/D)
3. **Adaptive DTE** — seleziona DTE basato su entry_score durante la creazione della position
4. **Rolling Sharpe** — weight il score sulla base dello Sharpe ratio recente della strategia
5. **Macro regime filter** — score boost/penality in base al macro regime corrente
