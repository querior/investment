# Frontend Configuration UI — Entry Score Parameters

**Status**: ✅ IMPLEMENTATO (2026-04-27)

---

## Overview

Aggiunti i parametri di configurazione dell'entry score al componente `ParameterEditor.tsx`, permettendo agli utenti di tunable tutti i 9 parametri entry score direttamente dal frontend durante il setup del backtest.

---

## File Modificati

### `ParameterEditor.tsx`
**Percorso**: `frontend/src/components/backtest/ParameterEditor.tsx`

#### Modifiche:

1. **Aggiunte 9 nuove hint descriptions** (linee 261-303)
   ```typescript
   "entry_size.multiplier_full"
   "entry_size.multiplier_reduced"
   "entry_score.dte_min"
   "entry_score.dte_optimal_min"
   "entry_score.dte_optimal_max"
   "entry_score.dte_max"
   "entry_score.rsi_neutral_min"
   "entry_score.rsi_neutral_max"
   ```

2. **Aggiunti 8 parametri all'array ENTRY_PARAMS** (linee 347-354)
   ```typescript
   // Entry scoring - DTE optimal range
   "entry_score.dte_min",
   "entry_score.dte_optimal_min",
   "entry_score.dte_optimal_max",
   "entry_score.dte_max",
   // Entry scoring - RSI neutrality
   "entry_score.rsi_neutral_min",
   "entry_score.rsi_neutral_max",
   // Size multipliers
   "entry_size.multiplier_full",
   "entry_size.multiplier_reduced",
   ```

---

## UI Layout

I parametri vengono visualizzati nella tab **"Entry"** del ParameterEditor in una grid 2-colonne:

### Entry Tab (visibile dopo le modifiche)

```
┌─────────────────────────────────────────────────────────┐
│ Entry                                                   │
├─────────────────────────────────────────────────────────┤
│ IV Min Threshold          │ RSI Min (Bull Put)          │
│ IV Min (Neutral)          │ IV/RV Ratio Min             │
│ Target Delta (Short)      │ Target Delta (Long)         │
│ Cooldown After Close      │ Max Risk                    │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ Weight: IV Rank           │ Weight: IV/HV Ratio         │
│ Weight: Squeeze           │ Weight: RSI Neutrality      │
│ Weight: DTE Score         │ Weight: Volume Ratio        │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ **DTE Minimum (days)**    │ **DTE Optimal Min (days)** │ ← NEW
│ **DTE Optimal Max (days)**│ **DTE Maximum (days)**      │ ← NEW
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ **RSI Neutral Min**       │ **RSI Neutral Max**         │ ← NEW
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│ Score Threshold (Full)    │ Score Threshold (Reduced)   │
│ **Size Multiplier (Full)**│ **Size Multiplier (Reduced)│ ← NEW
│                                                         │
│        [Cancel]                              [Save]    │
└─────────────────────────────────────────────────────────┘
```

---

## Hints & Descriptions

Ogni parametro ha una tooltip con descrizione dettagliata accessibile tramite click sull'icona `?`:

### Entry Size Multipliers
```
Multiplier (Full)
  "Position size multiplier when score > threshold_full (0-1).
   1.0 = 100% of nominal size."

Multiplier (Reduced)
  "Position size multiplier when score >= threshold_reduced (0-1).
   0.75 = 75% of nominal size."
```

### DTE Optimal Range
```
DTE Minimum (days)
  "Minimum days to expiration threshold. Below this = unfavorable timing."

DTE Optimal Min (days)
  "Start of optimal DTE range (days). Ideal entry between optimal_min and optimal_max."

DTE Optimal Max (days)
  "End of optimal DTE range (days). Typical: 35-45 for weekly strategies."

DTE Maximum (days)
  "Maximum days to expiration threshold. Above this = less theta decay."
```

### RSI Neutrality
```
RSI Neutral Min
  "Lower bound of RSI neutral zone (0-100). Typical: 40.
   Inside [40,60] = perfect momentum."

RSI Neutral Max
  "Upper bound of RSI neutral zone (0-100). Typical: 60.
   Inside [40,60] = perfect momentum."
```

---

## User Experience

### Default Values
All parameters loaded from backend `parameter_schema.py`:
- DTE range: 21, 35, 45, 55
- RSI range: 40, 60
- Size multipliers: 1.0, 0.75

### Field Rendering
- **Numeric fields**: `InputNumber` with min/max validation
- **Range validation**: Client-side (via Ant Design) + Server-side
- **Step precision**: 1 for days, 0.01 for multipliers

### Workflow
1. User opens "New Run" modal
2. Clicks "Configure Parameters"
3. Navigates to "Entry" tab
4. Scrolls down to "DTE" and "RSI" sections
5. Adjusts values as needed
6. Clicks "Save"
7. Parameters sent to backend API
8. Backend validates against `parameter_schema.py`

---

## Backend Integration

The ParameterEditor already integrates with:

1. **Types** (`BacktestRunDto`, `BacktestConfigDto`)
   - `currentRun.parameters` contains all parameter values
   - `backtestConfig.parameterSchema` provides schema (min/max/default)

2. **API Integration** (via Redux saga)
   - `onSave()` callback sends parameters to backend
   - Backend validates via `validate_parameters()`
   - Errors displayed to user

3. **Redux State**
   - Parameters stored in `backtest` reducer
   - Updates trigger backtest runs with new config

---

## Technical Details

### Component Props
```typescript
interface ParameterEditorProps {
  currentRun: BacktestRunDto;              // Current parameter values
  backtestConfig: BacktestConfigDto | null; // Schema with defaults
  onSave: (parameters: Record<string, string>) => void;
  onCancel: () => void;
  onEdit?: () => void;
  loading?: boolean;
  readOnly?: boolean;
}
```

### Parameter Flow
```
ParameterEditor (draft state)
        ↓
    onSave(params)
        ↓
Redux saga (BacktestSaga)
        ↓
API call to /backtests/{id}/runs/{run_id}/parameters
        ↓
Backend: validate_parameters() + save to DB
        ↓
Frontend updates BacktestRunDto
        ↓
ParameterEditor re-renders with new values
```

---

## Data Validation

### Client-Side
- Min/max enforcement via `InputNumber`
- Type checking (string/int/float/bool)
- Required fields via Form rules

### Server-Side
```python
# backend/app/backtest/parameter_schema.py
errors = validate_parameters(params)
# Returns list of validation errors
```

Validation covers:
- Type correctness
- Range checks (min ≤ value ≤ max)
- Unit normalization

---

## Next Steps

### Current State
- ✅ All 9 parameters visible in UI
- ✅ Hints and descriptions added
- ✅ Integration with existing component
- ✅ Backend schema validation ready

### Optional Enhancements

#### 1. Reorganize Entry Tab (Low Priority)
Group parameters into visual sections:
```
┌─ BASIC ENTRY FILTERS (existing)
├─ ENTRY SCORING WEIGHTS (existing)
├─ ENTRY SCORING — DTE RANGE (new section)
├─ ENTRY SCORING — RSI NEUTRALITY (new section)
└─ POSITION SIZING (existing)
```

Implementation:
- Add `<Divider />` between sections
- Add section titles (e.g., `<h4>DTE Optimal Range</h4>`)

#### 2. Scenario Presets (Medium Priority)
Add buttons to load pre-configured scenarios:
```
[Conservative] [Aggressive] [IV-Focused]
```

Implementation:
- Create scenario JSON configs
- Add "Load Scenario" buttons
- Pre-fill form with values

#### 3. Dynamic Help Text (Low Priority)
Show entry score formula breakdown:
```
Entry Score =
  30% × (100 - IV_Rank) +
  20% × (1 - IV/HV) +
  20% × Squeeze_Intensity +
  15% × RSI_Neutrality +
  10% × DTE_Score +
   5% × Volume_Ratio
```

---

## Testing Checklist

Before deploying:

- [ ] Parameters visible in Entry tab
- [ ] Hint tooltips display correctly
- [ ] Min/max validation works
- [ ] Values save to backend
- [ ] Backend validation triggers on invalid input
- [ ] Read-only mode displays values correctly
- [ ] Edit mode allows modification

---

## Compatibility

- ✅ Ant Design 5.x
- ✅ React 18.x
- ✅ Redux state management
- ✅ TypeScript
- ✅ Responsive 2-column grid layout

---

## References

- **ParameterEditor.tsx**: `frontend/src/components/backtest/ParameterEditor.tsx`
- **Backend Schema**: `backend/app/backtest/parameter_schema.py`
- **Framework**: Options Engine Framework v4, Sezione 5
- **Config Docs**: `docs/backtest/entry-score-parameters.md`

---

**Last Updated**: 2026-04-27
**Status**: Ready for Testing
**Deploy**: Can be deployed with backend changes
