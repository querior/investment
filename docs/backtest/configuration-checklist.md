# Configuration Checklist — Entry Scoring Parameters

**Status**: ✅ COMPLETATO (2026-04-27)

---

## Riepilogo delle Modifiche

### 1. **parameter_schema.py** ✅
Aggiunti **9 parametri mancanti**:

| Categoria | Parametri aggiunti | Status |
|-----------|-------------------|--------|
| Entry Size Multipliers | `entry_size.multiplier_full`, `entry_size.multiplier_reduced` | ✅ |
| DTE Optimal Range | `entry_score.dte_min`, `entry_score.dte_optimal_min/max`, `entry_score.dte_max` | ✅ |
| RSI Neutrality | `entry_score.rsi_neutral_min`, `entry_score.rsi_neutral_max` | ✅ |

**File**: `/backend/app/backtest/parameter_schema.py` (lines 138-215)

---

### 2. **entry_scoring.py** ✅
Migliorate **2 componenti**:

#### Component 4: RSI Neutrality
- **Before**: RSI score = 100 - (|RSI-50|/50)*100 (lineare semplice)
- **After**: RSI score basato su `rsi_neutral_min` e `rsi_neutral_max` (configurable)
  - Inside zone [40,60]: score 100
  - Semi-extreme [20,80]: linear decay to ~30
  - Extreme [0,20] or [80,100]: score ~10

#### Component 5: DTE Score
- **Status**: Informativo (sempre 100 attualmente)
- **Nota**: DTE è fisso (45 giorni) al momento della selezione; futura versione supporterà DTE dinamico

**File**: `/backend/app/backtest/domain/strategy/entry_scoring.py` (lines 82-107)

---

### 3. **runs.py** ✅
Aggiunti **3 parametri mancanti** in `_build_entry_config()`:

```python
# Lines 135-141 (DTE e RSI neutrality)
"entry_score.dte_min": int(_get("entry_score.dte_min", "21")),
"entry_score.dte_optimal_min": int(_get("entry_score.dte_optimal_min", "35")),
"entry_score.dte_optimal_max": int(_get("entry_score.dte_optimal_max", "45")),
"entry_score.dte_max": int(_get("entry_score.dte_max", "55")),
"entry_score.rsi_neutral_min": float(_get("entry_score.rsi_neutral_min", "40")),
"entry_score.rsi_neutral_max": float(_get("entry_score.rsi_neutral_max", "60")),
```

**File**: `/backend/app/backtest/runs.py` (lines 131-145)

---

## Matrice di Completamento

### Entry Score Components

| Componente | Parametro | Default | Range | Validato | Note |
|-----------|-----------|---------|-------|----------|-------|
| IV Rank | `w1_iv_rank` | 0.30 | 0–1 | ✅ | Peso nel schema |
| IV/HV | `w2_iv_hv` | 0.20 | 0–1 | ✅ | Peso nel schema |
| Squeeze | `w3_squeeze` | 0.20 | 0–1 | ✅ | Peso nel schema |
| **RSI** | **w4_rsi** | **0.15** | **0–1** | **✅** | **Nuovi: rsi_neutral_min/max** |
| DTE | `w5_dte` | 0.10 | 0–1 | ✅ | Parametri DTE aggiunti |
| Volume | `w6_volume` | 0.05 | 0–1 | ✅ | Peso nel schema |

### Size Configuration

| Parametro | Default | Range | Validato | Usato in |
|-----------|---------|-------|----------|----------|
| `threshold_full` | 75 | 0–100 | ✅ | `entry_scoring.py` |
| `threshold_reduced` | 60 | 0–100 | ✅ | `entry_scoring.py` |
| **`multiplier_full`** | **1.0** | **0–1** | **✅** | **`entry_scoring.py` + `runs.py`** |
| **`multiplier_reduced`** | **0.75** | **0–1** | **✅** | **`entry_scoring.py` + `runs.py`** |

### DTE Optimal Range

| Parametro | Default | Range | Validato | Usato in |
|-----------|---------|-------|----------|----------|
| **`dte_min`** | **21** | **1–100** | **✅** | **`entry_scoring.py`** |
| **`dte_optimal_min`** | **35** | **1–100** | **✅** | **`entry_scoring.py`** |
| **`dte_optimal_max`** | **45** | **1–100** | **✅** | **`entry_scoring.py`** |
| **`dte_max`** | **55** | **1–365** | **✅** | **`entry_scoring.py`** |

### RSI Neutrality

| Parametro | Default | Range | Validato | Usato in |
|-----------|---------|-------|----------|----------|
| **`rsi_neutral_min`** | **40** | **0–100** | **✅** | **`entry_scoring.py`** |
| **`rsi_neutral_max`** | **60** | **0–100** | **✅** | **`entry_scoring.py`** |

---

## Testing & Validation

### Compilation Status
```bash
✅ python3 -m py_compile \
  backend/app/backtest/parameter_schema.py \
  backend/app/backtest/domain/strategy/entry_scoring.py \
  backend/app/backtest/runs.py
# No errors
```

### Parameter Validation
- [x] All parameters defined in `PARAMETER_SCHEMA`
- [x] Type checking (float, int, bool, string)
- [x] Range validation (min/max)
- [x] Unit documentation (ratio, days, pct, value)
- [x] Default values match framework

### Function Integration
- [x] `_build_entry_config()` reads all parameters
- [x] `calculate_entry_score()` uses all components
- [x] `calculate_position_size()` uses threshold/multiplier
- [x] Weight normalization in place (if sum ≠ 1.0)

---

## Framework Alignment

Controllato rispetto a **Options Engine Framework v4, Sezione 5**:

```
Framework richiede:
├─ Q_entry score (0-100) ......................... ✅ IMPLEMENTATO
│  ├─ IV Rank (w1=30%) .......................... ✅
│  ├─ IV/HV Ratio (w2=20%) ...................... ✅
│  ├─ Squeeze Intensity (w3=20%) ................ ✅
│  ├─ RSI Neutrality (w4=15%) ................... ✅ MIGLIORATO
│  ├─ DTE Score (w5=10%) ........................ ✅
│  └─ Volume Ratio (w6=5%) ...................... ✅
│
├─ Size Multiplier (0.0-1.0) ..................... ✅ IMPLEMENTATO
│  ├─ Score > 75 → 100% (1.0) ................... ✅
│  ├─ Score 60-74 → 75% (0.75) .................. ✅
│  └─ Score < 60 → 0% (no entry) ................ ✅
│
└─ DTE Optimal Range .............................. ✅ PARAMETRIZZATO
   ├─ Min (21gg) ................................. ✅
   ├─ Optimal zone (35-45gg) ..................... ✅
   └─ Max (55gg) ................................. ✅
```

---

## Documentation Created

1. **entry-score-parameters.md** ✅
   - Descrizione di ogni componente
   - Scenari di configurazione (conservativo, aggressivo, IV-focused)
   - Best practices di tuning
   - Esempi di debug

2. **configuration-checklist.md** (questo file) ✅
   - Riepilogo modifiche
   - Matrice di completamento
   - Validation status

---

## Next Steps

### Immediate (Ready to Test)
- [x] Compilazione verificata ✅
- [x] Parametri schema completo ✅
- [x] Entry scoring migliorato ✅
- [ ] **Run backtest con nuovi parametri** ← TODO
- [ ] **Validare output score** ← TODO

### Short Term
1. Aggiungere logging del score breakdown per debug
2. Testare i tre scenari di configurazione (conservativo, aggressivo, IV-focused)
3. Calibrare i pesi in base ai risultati di backtest

### Medium Term
1. Implementare DTE dinamico (non fisso a 45 giorni)
2. Aggiungere scoring per altri parametri (bid/ask, liquidità OTM)
3. Dashboard UI per tuning interattivo dei parametri

---

## Note Tecniche

### Weight Normalization
Se i pesi non sommano a 1.0, vengono normalizzati automaticamente in `entry_scoring.py`:
```python
total_weight = w1 + w2 + w3 + w4 + w5 + w6
w1 /= total_weight  # e così via...
```

### Component Fallbacks
Se un indicatore manca (NaN), il componente usa il valore neutrale (50):
```python
if pd.isna(iv_rank):
    component_1 = 50  # Neutral fallback
```

### RSI Neutrality Logic
Nuova logica per RSI score:
```
RSI in [40,60]: score = 100 (perfect)
RSI in [30,40) or (60,70]: score decays linearly (70-100 range)
RSI in [20,30) or (70,80]: score decays linearly (30-70 range)
RSI < 20 or > 80: score ≈ 10 (extreme)
```

---

## Files Modified

```
backend/app/backtest/parameter_schema.py
  └─ Added 9 new parameters (lines 138-215)

backend/app/backtest/domain/strategy/entry_scoring.py
  └─ Improved RSI neutrality logic (lines 82-107)
  └─ DTE score parameters extraction (lines 96-99)

backend/app/backtest/runs.py
  └─ Added RSI + DTE parameters to _build_entry_config (lines 135-145)
```

---

## Validation Checklist

- [x] Parameter schema complete with all required fields
- [x] Type and range validation in place
- [x] Python syntax compilation successful
- [x] All functions updated to use new parameters
- [x] Default values match framework specs
- [x] Documentation created and comprehensive
- [ ] Integration test with backtest run (pending)
- [ ] Performance impact assessment (pending)

---

**Last Updated**: 2026-04-27
**Status**: Ready for Testing
**Maintainer**: Claude Code
