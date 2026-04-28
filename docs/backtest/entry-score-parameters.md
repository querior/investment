# Entry Score Parameters Configuration

**Documento di riferimento** — Parametri tunable per il sistema di scoring dell'entry.

---

## Overview

L'entry score composito viene calcolato in **6 componenti** con pesi configurabili. Il risultato (0-100) determina automaticamente la size della posizione (0-100% della nominal size).

```
Entry Score = w1*(100-IV_rank) + w2*(1-IV/HV) + w3*squeeze + w4*rsi_neut + w5*dte + w6*vol_ratio
    ↓
Position Size Multiplier (0.0 to 1.0)
    ↓
Contratti aperti = floor(risk_available / risk_per_contract * multiplier)
```

---

## Componenti dello Score

### 1. IV Rank (w1) — 30% by default
Identifica il regime di volatilità implicita.

| Parametro | Default | Range | Descrizione |
|-----------|---------|-------|-------------|
| `entry_score.w1_iv_rank` | 0.30 | 0.0–1.0 | Weight del componente IV Rank |

**Logica:**
- IV Rank bassa (< 30%) → score alto → entry preferito
- IV Rank alta (> 70%) → score basso → entry sconsigliato

---

### 2. IV/HV Ratio (w2) — 20% by default
Confronta la volatilità implicita (prezzo opzioni) vs realizzata (movimento reale).

| Parametro | Default | Range | Descrizione |
|-----------|---------|-------|-------------|
| `entry_score.w2_iv_hv` | 0.20 | 0.0–1.0 | Weight del componente IV/HV |

**Logica:**
- IV/HV < 1.0 → opzioni economiche (cheap) → score alto
- IV/HV > 1.2 → opzioni care (expensive) → score basso

---

### 3. Squeeze Intensity (w3) — 20% by default
Misura la compressione della volatilità (setup di breakout).

| Parametro | Default | Range | Descrizione |
|-----------|---------|-------|-------------|
| `entry_score.w3_squeeze` | 0.20 | 0.0–1.0 | Weight del componente Squeeze |
| `squeeze.bb_percentile` | 20 | 5–50 | Percentile BB width per definire squeeze |
| `squeeze.macd_threshold` | 0.5 | 0.0–10.0 | Threshold MACD flatness |

**Logica:**
- Bollinger Bands width nel bottom 20% (tight) → squeeze attivo → score alto
- MACD piatto (|MACD| < threshold) → momentum neutro → bonus score

---

### 4. RSI Neutrality (w4) — 15% by default
Identifica momentum neutrale (migliore per entry).

| Parametro | Default | Range | Descrizione |
|-----------|---------|-------|-------------|
| `entry_score.w4_rsi` | 0.15 | 0.0–1.0 | Weight del componente RSI |
| `entry_score.rsi_neutral_min` | 40 | 0.0–100.0 | RSI min zona neutra |
| `entry_score.rsi_neutral_max` | 60 | 0.0–100.0 | RSI max zona neutra |

**Logica:**
- RSI 40-60 (inside neutral zone) → score 100
- RSI 20-80 (semi-extreme) → score decays linearly to ~30
- RSI < 20 or > 80 (extreme) → score ~10

---

### 5. DTE Score (w5) — 10% by default
Timing della scadenza del contratto opzionale (giorni a scadenza).

| Parametro | Default | Range | Descrizione |
|-----------|---------|-------|-------------|
| `entry_score.w5_dte` | 0.10 | 0.0–1.0 | Weight del componente DTE |
| `entry_score.dte_min` | 21 | 1–100 | DTE minimo accettabile |
| `entry_score.dte_optimal_min` | 35 | 1–100 | DTE inizio zona ottimale |
| `entry_score.dte_optimal_max` | 45 | 1–100 | DTE fine zona ottimale |
| `entry_score.dte_max` | 55 | 1–365 | DTE massimo accettabile |

**Logica:**
- DTE 35-45 (optimal range) → score 100
- DTE 21-35 o 45-55 (acceptable) → score decay
- DTE < 21 o > 55 (outside acceptable) → score low

**Nota:** Attualmente il DTE viene calcolato fisso (45 giorni) al momento della selezione della strategia. Il DTE score è informativo per future ottimizzazioni dinamiche.

---

### 6. Volume Ratio (w6) — 5% by default
Misura la compressione/espansione del volume.

| Parametro | Default | Range | Descrizione |
|-----------|---------|-------|-------------|
| `entry_score.w6_volume` | 0.05 | 0.0–1.0 | Weight del componente Volume |
| `volume.sma_period` | 20 | 5–100 | Periodo SMA per volume baseline |

**Logica:**
- Volume ratio 0.7-1.0 (contrazione) → score 50-100
- Volume ratio 1.0-1.5 (espansione) → score 100-50
- Volume ratio < 0.5 o > 1.5 (estremo) → score ~30

---

## Sizing della Posizione

Il score (0-100) si converte in size multiplier (0.0 a 1.0):

| Parametro | Default | Range | Descrizione |
|-----------|---------|-------|-------------|
| `entry_size.threshold_full` | 75 | 0.0–100.0 | Score soglia per full size |
| `entry_size.threshold_reduced` | 60 | 0.0–100.0 | Score soglia per reduced size |
| `entry_size.multiplier_full` | 1.0 | 0.0–1.0 | Multiplier quando score > threshold_full |
| `entry_size.multiplier_reduced` | 0.75 | 0.0–1.0 | Multiplier quando 60 ≤ score ≤ 75 |

**Logica:**
```
if entry_score > 75:
    multiplier = 1.0          # Full size (100%)
elif entry_score >= 60:
    multiplier = interpolate  # Linear between 0.75 and 1.0
else:
    multiplier = 0.0          # No entry
```

---

## Esempi di Configurazione

### Scenario Conservativo
Per backtest con rischio ridotto e qualità entry alta:

```python
{
    "entry_score.w1_iv_rank": 0.35,      # +5% weight IV
    "entry_score.w2_iv_hv": 0.20,
    "entry_score.w3_squeeze": 0.20,
    "entry_score.w4_rsi": 0.15,
    "entry_score.w5_dte": 0.05,          # -5% weight DTE
    "entry_score.w6_volume": 0.05,

    "entry_size.threshold_full": 80,     # +5 score più stretto
    "entry_size.threshold_reduced": 65,  # +5 score più stretto
}
```

### Scenario Aggressivo
Per massimizzare il numero di trade:

```python
{
    "entry_score.w1_iv_rank": 0.25,      # -5% weight IV (meno selettivo su regime)
    "entry_score.w2_iv_hv": 0.20,
    "entry_score.w3_squeeze": 0.20,
    "entry_score.w4_rsi": 0.20,          # +5% weight RSI
    "entry_score.w5_dte": 0.10,
    "entry_score.w6_volume": 0.05,

    "entry_size.threshold_full": 70,     # -5 score più largo
    "entry_size.threshold_reduced": 55,  # -5 score più largo
}
```

### Scenario IV-Focused
Per trading basato principalmente su regime volatilità:

```python
{
    "entry_score.w1_iv_rank": 0.40,      # +10% weight IV
    "entry_score.w2_iv_hv": 0.25,        # +5% weight IV/HV
    "entry_score.w3_squeeze": 0.15,      # -5% weight squeeze
    "entry_score.w4_rsi": 0.10,          # -5% weight RSI
    "entry_score.w5_dte": 0.05,
    "entry_score.w6_volume": 0.05,
}
```

---

## Validazione dei Parametri

I parametri sono validati automaticamente nel backend:

1. **Range check** — Ogni valore deve rispettare min/max definiti
2. **Weight normalization** — Se somma pesi ≠ 1.0, vengono normalizzati automaticamente
3. **Type validation** — Conversione a float/int con controllo

Esempio:
```python
# Se si passa:
entry_score.w1_iv_rank = 0.35
entry_score.w2_iv_hv = 0.25
entry_score.w3_squeeze = 0.20
entry_score.w4_rsi = 0.15
entry_score.w5_dte = 0.10
entry_score.w6_volume = 0.05
# Somma = 1.10 ≠ 1.0
# → Normalizza a: [0.318, 0.227, 0.182, 0.136, 0.091, 0.045]
```

---

## Best Practices di Tuning

1. **Cominciate con i default** — Sono basati sul framework e testati
2. **Cambiate un peso alla volta** — Per identificare l'effetto
3. **Monitorate il signal quality** — Rapporto trades vs winrate
4. **Adattate al regime corrente**:
   - IV bassa → aumentate w1 (IV Rank)
   - Squeeze attivo → aumentate w3
   - Trend forte → riducete w4 (RSI)
5. **Ribilanciate i pesi** — La somma deve rimanere ~1.0

---

## Collaudo e Debug

Per vedere i componenti del score durante il backtest:

```python
# In runs.py, aggiungere log:
print(f"Entry score components: "
      f"iv_rank={component_1:.0f}, "
      f"iv_hv={component_2:.0f}, "
      f"squeeze={component_3:.0f}, "
      f"rsi={component_4:.0f}, "
      f"dte={component_5:.0f}, "
      f"vol={component_6:.0f} "
      f"→ total={entry_score:.0f} "
      f"→ size_multiplier={size_multiplier:.2f}")
```

---

## Riferimenti

- **Framework**: Options Engine Framework v4, Sezione 5
- **Implementazione**: `entry_scoring.py`
- **Config builder**: `runs.py::_build_entry_config()`
- **Schema parametri**: `parameter_schema.py`
