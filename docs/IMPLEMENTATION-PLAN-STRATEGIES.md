# Implementation Plan — Decision Layer + All Strategies

**Scope**: Implementare decision layer completo (L1-L5) + tutte le 10 strategie mancanti

**Session**: 2026-04-28
**Status**: ✅ FASE 0-3 COMPLETE (69 tests passing)

---

## Status Attuale

### ✅ Già Implementate (3/13)
| Famiglia | Strategia | File | Status |
|----------|-----------|------|--------|
| 2 | Bull Put Spread | bull_put.py | ✅ |
| 2 | Bear Call Spread | bear_call.py | ✅ |
| 5 | Broken Wing Butterfly | neutral_broken_wing.py | ✅ |

### ❌ Mancanti (10/13) — Da implementare questa sessione
| Famiglia | Strategia | Fase |
|----------|-----------|------|
| **1** | Bull Call Spread | Fase 1 |
| **1** | Bear Put Spread | Fase 1 |
| **3** | Long Straddle | Fase 1 |
| **3** | Long Strangle | Fase 1 |
| **4** | Iron Condor | Fase 1 |
| **4** | Iron Butterfly | Fase 1 |
| **5** | Calendar Spread | Fase 1 |
| **5** | Jade Lizard | Fase 1 |
| **5** | Reverse Jade Lizard | Fase 1 |
| **5** | Diagonal Spread | Fase 1 |

---

## Architettura Target

```
domain/
├── strategy/
│   ├── base.py              # StrategySpec dataclass
│   ├── strategy_builder.py  # Builders (create_* functions) — 10 nuove
│   ├── bull_put.py          # bull_put_strategy()
│   ├── bear_call.py         # bear_call_strategy()
│   ├── neutral_broken_wing.py # neutral_broken_wing_strategy()
│   ├── bull_call.py         # NEW
│   ├── bear_put.py          # NEW
│   ├── long_straddle.py     # NEW
│   ├── long_strangle.py     # NEW
│   ├── iron_condor.py       # NEW
│   ├── iron_butterfly.py    # NEW
│   ├── calendar_spread.py   # NEW
│   ├── jade_lizard.py       # NEW
│   ├── reverse_jade_lizard.py # NEW
│   ├── diagonal_spread.py   # NEW
│   ├── no_trade.py
│   └── selectors.py         # select_strategy() — REFACTOR
│
└── decision/                # NEW PACKAGE — Multi-level decision
    ├── __init__.py
    ├── models.py            # Zone, Trend enums + dataclasses
    ├── zone_classifier.py   # L1: IV_rank + ADX → Zone
    ├── strategy_selector.py # L2: Zone + Trend → StrategySpec
    ├── pricing.py           # L3: Strike selection + Greeks
    ├── greeks_calculator.py # L3: Delta/Gamma/Vega/Theta aggregation
    ├── opportunity_evaluator.py # L4: Multi-dim scoring
    └── trade_decision.py    # L5: Final OPEN/SKIP/MONITOR gate
```

---

## Piano di Implementazione — REORDERED

### ✅ FASE 0: Decision Layer Foundation (L1) — COMPLETE
**Setup decision package + Zone Classification**

Objectives:
- [x] Create `domain/decision/` package
- [x] Implement `models.py` (Zone, Trend, StrategySpec enums)
- [x] Implement `zone_classifier.py` with `classify_zone(iv_rank, adx) → Zone`
- [x] Unit tests: 22 tests, all passing

**Files**: 3 new
**LOC**: ~200
**Tests**: ✅ 22/22 passing

---

### FASE 1: All 10 Missing Strategies
**Implement builders + strategy wrappers + integrate into STRATEGY_MATRIX**

#### Builders in `strategy_builder.py` (10 nuove funzioni):

**Famiglia 1 — Debit Spreads (Zone A: Trend + Low IV)**
- [ ] `create_bull_call_spread()` — Long Call + Short Call (UP trend)
- [ ] `create_bear_put_spread()` — Short Put + Long Put (DOWN trend)

**Famiglia 3 — Long Volatility (Zone C: Lateral + Low IV)**
- [ ] `create_long_straddle()` — Long Call ATM + Long Put ATM (high squeeze)
- [ ] `create_long_strangle()` — Long Call OTM + Long Put OTM (medium squeeze)

**Famiglia 4 — Combined Spreads (Zone D: Lateral + High IV)**
- [ ] `create_iron_condor()` — 4 gambe (short put/call OTM, long put/call more OTM)
- [ ] `create_iron_butterfly()` — 4 gambe (short straddle ATM, long strangle OTM)

**Famiglia 5 — Advanced (Zone B/D: Theta + Vol)**
- [ ] `create_calendar_spread()` — Short near + Long far (same strike, diff DTE)
- [ ] `create_jade_lizard()` — Short Put + Short Call + Long Call (Zone B UP, Zone D neutral)
- [ ] `create_reverse_jade_lizard()` — Short Call + Short Put + Long Put (Zone B DOWN)
- [ ] `create_diagonal_spread()` — Short near + Long far (diff strikes + diff DTE)

#### Strategy Wrappers (10 nuovi file):
- [ ] `bull_call.py`, `bear_put.py`
- [ ] `long_straddle.py`, `long_strangle.py`
- [ ] `iron_condor.py`, `iron_butterfly.py`
- [ ] `calendar_spread.py`, `jade_lizard.py`, `reverse_jade_lizard.py`, `diagonal_spread.py`

#### Integration with STRATEGY_MATRIX:
- [ ] Verify all 10 strategies importable in decision/strategy_selector.py
- [ ] STRATEGY_MATRIX includes all 10 (Zone A, B, C, D mappings)

**Pattern** (ogni file):
```python
from .strategy_builder import create_xxx_yyy
from .base import StrategySpec

def xxx_yyy_strategy() -> StrategySpec:
    return StrategySpec(
        name="xxx_yyy",
        builder=create_xxx_yyy,
        should_trade=True,
    )
```

**Files**: 11 (1 expanded + 10 new)
**LOC**: ~800
**Tests**: ✅ All strategy tests included in phase 2

---

### ✅ FASE 2: Decision Layer L2 (Strategy Selector) — COMPLETE
**Implement STRATEGY_MATRIX + select_strategy()**

Objectives:
- [x] Implement `strategy_selector.py` with `STRATEGY_MATRIX`
- [x] Implement `select_strategy(zone, trend, squeeze_intensity, iv_rank, entry_score) → StrategySpec`
- [x] Implement `rank_strategies()` to resolve ambiguity
- [x] Refactor `selectors.py` to use new decision layer
- [x] Unit tests: 23 tests, all passing

**STRATEGY_MATRIX Structure**: Fully implemented per spec

**Files**: 2 (1 new + 1 refactored)
**LOC**: ~300
**Tests**: ✅ 23/23 passing

---

### ✅ FASE 3: Decision Layer L3 (Pricing & Greeks) — COMPLETE
**Implement pricing calculation + Greeks aggregation**

Objectives:
- [x] Implement `pricing.py` with `PricingContext` dataclass (15 fields)
- [x] Implement `calculate_pricing(spec, row, params) → PricingContext`
- [x] Generic pricing approach: Black-Scholes with position aggregation
- [x] Implement `greeks_calculator.py` (Delta, Gamma, Vega, Theta using scipy)
- [x] Unit tests: 32 tests (Black-Scholes, Greeks, PricingContext with all 13 strategies)

**Files**: 2
**LOC**: ~400
**Tests**: ✅ 32/32 passing
  - Black-Scholes: 8 tests (ITM/OTM/ATM, zero vol)
  - Greeks Calculators: 11 tests (properties, boundaries, aggregation)
  - PricingContext: 2 tests (manual + parametrized over all 13 strategies)
  - Calculate Pricing: 11 tests (spot/IV/DTE variations, fallbacks, multi-leg)

---

### FASE 4: Decision Layer L4 (Opportunity Evaluation)
**Implement multi-dimensional scoring**

Objectives:
- [ ] Implement `opportunity_evaluator.py` with `OpportunityEvaluation` dataclass
- [ ] Implement 5 scoring dimensions:
  - Pricing edge (35% weight) — Fair value vs market
  - Risk/reward ratio (25% weight) — Max gain vs max loss
  - Breakeven reachability (20% weight) — Sigmas to BEP
  - Execution cost (15% weight) — Bid/Ask spread impact
  - Capital efficiency (5% weight) — Profit per $ rischiato
- [ ] Implement `evaluate_opportunity(pricing, entry_config, risk_config) → OpportunityEvaluation`
- [ ] Unit tests: scoring dimensions

**Files**: 1
**LOC**: ~300
**Time**: 1.5 hours

---

### FASE 5: Decision Layer L5 (Trade Decision)
**Implement final trade decision gate**

Objectives:
- [ ] Implement `trade_decision.py` with `TradeDecision` dataclass
- [ ] Implement `make_trade_decision(evaluation, config) → TradeDecision`
- [ ] Decision logic: OPEN (score > 75) / SKIP (score < 60) / MONITOR (60-75)
- [ ] Unit tests: decision logic

**Files**: 1
**LOC**: ~200
**Time**: 0.5 hours

---

### FASE 6: Integration & Configuration
**Connect all layers to backtest loop**

Objectives:
- [ ] Update `parameter_schema.py` — Add decision layer config params
  - decision.opportunity_threshold (default 75)
  - decision.breakeven_threshold (default 1.5 sigmas)
  - decision.max_bid_ask_pct (default 15%)
  - opportunity.weight_* (5 weights for dimensions)
- [ ] Update `runs.py` — Integrate full decision pipeline
- [ ] Update `selectors.py` — Use zone_classifier + strategy_selector

**Files**: 3 (modified)
**LOC**: ~200
**Time**: 1 hour

---

### FASE 7: Testing & Validation
**Complete test coverage**

Objectives:
- [ ] Unit tests: zone_classifier (4 zones + edges)
- [ ] Unit tests: strategy_selector (all zones)
- [ ] Unit tests: pricing (13 strategies)
- [ ] Unit tests: opportunity_evaluator (all dimensions)
- [ ] Unit tests: trade_decision (OPEN/SKIP/MONITOR)
- [ ] Integration tests: full pipeline (signals → decision)
- [ ] Regression tests: existing backtest results unchanged

**LOC**: ~500
**Time**: 2-3 hours

---

## Implementation Timeline & Estimates

| Fase | Task | Files | LOC | Time | Status |
|------|------|-------|-----|------|--------|
| **0** | Models + L1 Zone Classifier | 3 | ~200 | 1h | ✅ DONE |
| **1** | 10 Strategies (builders + wrappers) | 11 | ~730 | 2.5h | ✅ DONE |
| **2** | L2 Strategy Selector | 2 | ~300 | 1h | ✅ DONE |
| **3** | L3 Pricing & Greeks | 2 | ~400 | 2h | ⏳ NEXT |
| **4** | L4 Opportunity Evaluator | 1 | ~300 | 1.5h | ⏳ TODO |
| **5** | L5 Trade Decision | 1 | ~200 | 0.5h | ⏳ TODO |
| **6** | Integration & Config | 3 | ~200 | 1h | ⏳ TODO |
| **7** | Testing & Validation | — | ~500 | 2-3h | ⏳ TODO |
| **TOTAL** | | **23 files** | **~2900 LOC** | **11-13h** | |

---

## Detailed Implementation Flow

### Decision Layer Flow (In Backtest Loop)
```python
# runs.py process_entry_signal()

# Level 1: Zone Classification
zone = classify_zone(row['iv_rank'], row['adx'])
logger.info(f"[L1] Zone: {zone}")

# Level 2: Strategy Selection
strategy_spec = select_strategy(
    zone=zone,
    trend=row['trend_signal'],
    squeeze_intensity=row['squeeze_intensity'],
    iv_rank=row['iv_rank'],
    entry_score=calculate_entry_score(row, entry_config),
)
logger.info(f"[L2] Strategy: {strategy_spec.name}")

# Level 3: Pricing & Greeks
pricing = calculate_pricing(strategy_spec, row, entry_config)
logger.info(f"[L3] Pricing: fair={pricing.fair_value}, edge={pricing.edge}")

# Level 4: Opportunity Evaluation
evaluation = evaluate_opportunity(pricing, entry_config, risk_config)
logger.info(f"[L4] Score: {evaluation.overall_score:.0f}/100")

# Level 5: Trade Decision
decision = make_trade_decision(evaluation, position_config)
logger.info(f"[L5] Decision: {decision.action}")

if decision.action == "OPEN":
    position = strategy_spec.builder(...)
    portfolio.open_position(position)
```

---

## Testing Strategy

### Unit Tests (by Fase)
- **Fase 0**: Zone classification (4 zones + edge cases)
- **Fase 1**: Strategy builders (10 builders → Position structure)
- **Fase 2**: Strategy selector (MATRIX logic per zone)
- **Fase 3**: Pricing (fair value + Greeks for each strategy)
- **Fase 4**: Opportunity scoring (5 dimensions + weights)
- **Fase 5**: Trade decision (OPEN/SKIP/MONITOR logic)

### Integration Tests
- Full pipeline: Signals → Decision
- Entry score impact: Change score → decision changes
- Risk limiting: Reject if max_loss > limit
- Liquidity filter: Reject if bid/ask > 15%

### Regression Tests
- Existing backtest results unchanged
- size_multiplier applied correctly
- No regressions in bull_put, bear_call strategies

---

## Rollout Strategy

### Single Session Approach ✅ **CHOSEN**
- Implement FASE 0-7 in one continuous session
- Test at each level before moving to next
- Validate end-to-end pipeline
- ✅ Complete + Consistent + Ready for production

---

## Acceptance Criteria

### Code Quality
- [ ] All 23 files compile without errors
- [ ] All 10 strategy builders working (Position structure correct)
- [ ] All 7 decision layer modules integrated
- [ ] Zero regressions on existing strategies (bull_put, bear_call)
- [ ] Code follows project conventions (snake_case, no top-level imports in functions)

### Functional Requirements
- [ ] Zone classifier returns correct zone for IV_rank + ADX combinations
- [ ] Strategy selector returns StrategySpec for each zone/trend
- [ ] Pricing calculates fair value + Greeks for all 13 strategies
- [ ] Opportunity evaluator scores range 0-100 with clear reasoning
- [ ] Trade decision: OPEN (>75), SKIP (<60), MONITOR (60-75)
- [ ] All parameters tunable from parameter_schema.py

### Integration Requirements
- [ ] ParameterEditor recognizes all decision layer params
- [ ] Full pipeline runs in backtest loop (L1→L5)
- [ ] Backtest executes with at least 3 new strategies
- [ ] Logging shows all 5 decision levels

### Documentation
- [ ] Docstring for each builder and strategy
- [ ] Zone → Strategy matrix documented
- [ ] Decision flow diagram in ARCHITECTURE-DECISION-LAYER.md
- [ ] Examples of entry/exit per zone + strategy

---

## Order of Execution

```
[FASE 0] → [FASE 1] → [FASE 2] → [FASE 3] → [FASE 4] → [FASE 5] → [FASE 6] → [FASE 7]
   L1        Strategies    L2         L3         L4         L5        Integration  Testing
   1h        2-3h          1h         2h         1.5h       0.5h      1h            2-3h
```

**Dependencies**:
- FASE 1 (strategies) must complete before FASE 2 (selector uses them)
- FASE 2 (selector) must complete before FASE 3 (pricing uses selector output)
- All FASE 0-5 must complete before FASE 6 (integration)
- All FASE 0-6 must complete before FASE 7 (testing)

---

## Refactoring — Engine Extraction (Post-FASE 5)

After FASE 5, the decision layer (L1→L5) was refactored out of the backtest module into a standalone, reusable engine:

**Changes**:
- Moved `app/backtest/domain/decision/` → `app/engines/option/`
- Created `app/engines/option/engine.py` — **DecisionEngine** class (L1→L5 orchestration)
- Repositioned tests: `tests/backtest/domain/decision/` → `tests/engines/option/`
- Updated imports throughout the codebase

**Rationale**:
The decision logic for option strategies is business logic, not backtest-specific. Extracting it to `app/engines/option/` allows reuse across:
- Backtest (historical data)
- Live trading (real-time data)
- API endpoints (decision-as-a-service)
- Frontend (decision preview)

**Status**: ✅ FASE 0-5 COMPLETE + REFACTORING DONE (122 tests passing)
**Next Action**: FASE 6 — Integrate DecisionEngine into backtest loop
