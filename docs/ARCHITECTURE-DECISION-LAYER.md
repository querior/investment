# Decision Layer Architecture — Multi-Level Strategy Selection

**Goal**: Strutturare il decision process da segnali → strategia → pricing → valutazione → trade decision

---

## Overview Architettura

```
┌─────────────────────────────────────────────────────────────┐
│ Market Data (row)                                           │
│ - IV, IV_rank, ADX, RSI, Squeeze, Volume, Macro, etc.     │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────▼───────────────┐
        │ [L1] Zone Classification   │
        │ IV_rank + ADX              │
        │ Result: A / B / C / D      │
        └────────────┬───────────────┘
                     │
        ┌────────────▼──────────────────┐
        │ [L2] Strategy Selection        │
        │ Zone + Trend + Macro + Entry   │
        │ Result: StrategySpec           │
        └────────────┬──────────────────┘
                     │
        ┌────────────▼──────────────────┐
        │ [L3] Pricing & Greeks          │
        │ Strike selection + Delta calc  │
        │ Result: PricingContext         │
        └────────────┬──────────────────┘
                     │
        ┌────────────▼──────────────────┐
        │ [L4] Opportunity Evaluation    │
        │ Fair value + risk/reward       │
        │ Result: OpportunityScore       │
        └────────────┬──────────────────┘
                     │
        ┌────────────▼──────────────────┐
        │ [Final] Trade Decision         │
        │ Score > threshold?             │
        │ Risk within limits?            │
        └────────────┬──────────────────┘
                     │
              ✓ OPEN TRADE
              ✗ NO TRADE
```

---

## Level 1: Zone Classification

**Input**: IV_rank, ADX
**Output**: Zone ("A", "B", "C", "D", "UNKNOWN")
**Framework Ref**: Options Engine v4, Sezione 6

### Matrice Classificazione
```python
class Zone(Enum):
    A = "A"  # Direzionale + IV bassa    → Long vol + bias
    B = "B"  # Direzionale + IV alta     → Credit spreads
    C = "C"  # Laterale + IV bassa       → Straddle/Strangle
    D = "D"  # Laterale + IV alta        → Iron Condor/Butterfly
```

### Logica
```python
def classify_zone(iv_rank: float, adx: float) -> Zone:
    trend = "directional" if adx > 25 else "lateral"
    iv = "low" if iv_rank < 30 else "high"

    if trend == "directional" and iv == "low":
        return Zone.A
    elif trend == "directional" and iv == "high":
        return Zone.B
    elif trend == "lateral" and iv == "low":
        return Zone.C
    elif trend == "lateral" and iv == "high":
        return Zone.D
    else:
        return Zone.UNKNOWN
```

### File
```
domain/decision/
├── zone_classifier.py  (NEW)
│   └── classify_zone(iv_rank, adx) → Zone
```

---

## Level 2: Strategy Selection

**Input**: Zone, Trend, RSI, Macro, Squeeze, Entry Score
**Output**: StrategySpec (name, builder, size_multiplier)
**Framework Ref**: Options Engine v4, Sezione 7 (Matrice Strategia per Regime)

### Decision Matrix
```python
STRATEGY_MATRIX = {
    # Zone A: Direzionale + IV bassa
    Zone.A: {
        Trend.UP: [bull_call_spread_strategy],
        Trend.DOWN: [bear_put_spread_strategy],
        Trend.NEUTRAL: [broken_wing_butterfly_strategy],
    },

    # Zone B: Direzionale + IV alta
    Zone.B: {
        Trend.UP: [bull_put_spread_strategy, jade_lizard_strategy],
        Trend.DOWN: [bear_call_spread_strategy, reverse_jade_lizard_strategy],
        Trend.NEUTRAL: [no_trade],
    },

    # Zone C: Laterale + IV bassa
    Zone.C: {
        "high_squeeze": [long_straddle_strategy],
        "medium_squeeze": [long_strangle_strategy],
        "low_squeeze": [broken_wing_butterfly_strategy],
    },

    # Zone D: Laterale + IV alta
    Zone.D: {
        "very_high_iv": [iron_butterfly_strategy],
        "high_iv": [iron_condor_strategy, calendar_spread_strategy],
        "neutral": [jade_lizard_strategy, diagonal_spread_strategy],
    },
}
```

### Selezione Sequenziale
```python
def select_strategy(
    zone: Zone,
    trend: Trend,
    squeeze_intensity: float,
    iv_rank: float,
    entry_score: float,  # 0-100
) -> StrategySpec:
    """
    1. Lookup candidates in STRATEGY_MATRIX
    2. Filter by additional conditions (squeeze, macro, etc)
    3. Rank by entry_score
    4. Return top candidate with size_multiplier
    """
    candidates = STRATEGY_MATRIX[zone][trend]

    # Filter by squeeze/IV conditions
    filtered = [s for s in candidates if passes_conditions(s)]

    # No candidates → no trade
    if not filtered:
        return no_trade_strategy()

    # Single candidate → return with size_multiplier
    if len(filtered) == 1:
        spec = filtered[0]()
        spec.size_multiplier = calculate_position_size(entry_score)
        return spec

    # Multiple candidates → rank by entry_score or other metrics
    best = rank_strategies(filtered, entry_score, iv_rank)
    best.size_multiplier = calculate_position_size(entry_score)
    return best
```

### File
```
domain/decision/
├── strategy_selector.py  (REFACTOR from selectors.py)
│   ├── STRATEGY_MATRIX
│   ├── select_strategy(zone, trend, ...) → StrategySpec
│   └── rank_strategies(...) → StrategySpec
```

---

## Level 3: Pricing & Greeks

**Input**: StrategySpec, Market Data (S, IV, DTE)
**Output**: PricingContext (fair_value, delta, greche, strikes)

### Pricing Context
```python
@dataclass
class PricingContext:
    strategy_name: str
    spot: float
    iv: float
    dte_days: int

    # Strikes
    strikes: dict[str, float]  # {"short": 200, "long": 195, ...}

    # Greeks (aggregate per position)
    delta: float               # Position delta
    gamma: float
    vega: float
    theta: float

    # Pricing
    market_price: float        # Bid/Ask mid
    fair_value: float          # Black-Scholes theo
    bid_ask_spread: float      # $ spread
    bid_ask_pct: float         # % spread

    # Entry quality
    edge: float                # fair_value - market_price
    breakeven_distance: float  # % above/below spot
```

### Pricing Pipeline

Generic approach: Build position from spec, price each leg via Black-Scholes, aggregate Greeks.

```python
def calculate_pricing(
    spec: StrategySpec,
    row: pd.Series,           # Market data row (close, iv, dte_days, etc)
    entry_config: dict,       # Config with delta targets, pricing params
) -> PricingContext:
    """
    Generic pricing pipeline (works for all 13 strategies):
    
    1. Build Position using spec.builder
    2. For each leg: price via Black-Scholes, calculate Greeks
    3. Aggregate Greeks across all legs (respecting +1/-1 signs)
    4. Calculate fair_value and market_price
    5. Compute edge and breakeven distance
    
    Returns: PricingContext with all pricing and Greeks
    """
    spot = row['close']
    iv = row['iv']
    dte_days = int(row.get('dte_days', 45))
    
    # Build position from strategy spec
    position = spec.builder(
        date=row['date'],
        S=spot,
        iv=iv,
        dte_days=dte_days,
        target_delta_short=entry_config.get('target_delta_short', 0.16),
        target_delta_long=entry_config.get('target_delta_long', 0.05),
        quantity=1,  # Normalized for pricing
    )
    
    # Price each leg + calculate Greeks
    total_delta = total_gamma = total_vega = total_theta = 0.0
    
    for leg in position.legs:
        # Black-Scholes pricing
        leg_price = black_scholes(S=spot, K=leg.state.K, T=leg.state.T, 
                                  sigma=iv, r=leg.state.r,
                                  option_type=leg.state.option_type)
        
        # Greeks for this leg
        leg_delta = calculate_delta(K=leg.state.K, S=spot, sigma=iv, 
                                    T=leg.state.T, option_type=leg.state.option_type)
        leg_gamma = calculate_gamma(K=leg.state.K, S=spot, sigma=iv, T=leg.state.T)
        leg_vega = calculate_vega(K=leg.state.K, S=spot, sigma=iv, T=leg.state.T)
        leg_theta = calculate_theta(K=leg.state.K, S=spot, sigma=iv, T=leg.state.T,
                                    option_type=leg.state.option_type, r=leg.state.r)
        
        # Aggregate with position sign (+1 = long, -1 = short)
        total_delta += leg_delta * leg.sign
        total_gamma += leg_gamma * leg.sign  # Gamma always positive impact
        total_vega += leg_vega * leg.sign
        total_theta += leg_theta * leg.sign
    
    # Fair value: sum of all legs with their signs
    fair_value = sum(
        black_scholes(...) * leg.sign
        for leg in position.legs
    )
    
    # Market price (use input or fallback to fair value)
    market_price = row.get('market_price', fair_value)
    bid_ask_pct = row.get('bid_ask_pct', 0.02)
    bid_ask_spread = market_price * bid_ask_pct
    
    # Edge: our profit if buy at market and sell at fair value
    edge = fair_value - market_price
    
    # Breakeven distance (simplified)
    breakeven_distance = fair_value / spot if spot > 0 else 0
    
    return PricingContext(
        strategy_name=spec.name,
        spot=spot, iv=iv, dte_days=dte_days,
        strikes={f"leg_{i}": leg.state.K for i, leg in enumerate(position.legs)},
        delta=total_delta, gamma=total_gamma, vega=total_vega, theta=total_theta,
        market_price=market_price, fair_value=fair_value,
        bid_ask_spread=bid_ask_spread, bid_ask_pct=bid_ask_pct,
        edge=edge, breakeven_distance=breakeven_distance,
    )
```

### Files
```
domain/decision/
├── pricing.py  (NEW)
│   ├── PricingContext (dataclass)
│   ├── calculate_pricing(spec, row, entry_config) → PricingContext
│   ├── black_scholes(S, K, T, sigma, r, option_type) → float
│   └── calculate_breakeven_distance(...) → float
│
└── greeks_calculator.py  (NEW)
    ├── calculate_delta(K, S, sigma, T, option_type) → float
    ├── calculate_gamma(K, S, sigma, T) → float
    ├── calculate_vega(K, S, sigma, T) → float
    └── calculate_theta(K, S, sigma, T, option_type, r) → float
```

**Design Pattern**: Generic approach using Black-Scholes + Greek formulas for all strategies. No strategy-specific pricing functions needed.

---

## Level 4: Opportunity Evaluation

**Input**: PricingContext, Risk Params
**Output**: OpportunityScore (0-100) + reason

### Concetto di Opportunità

Prima di aprire una posizione in opzioni, devi sapere: "Quanto è buona davvero questa opportunità?" Non basta che sia redditizia in teoria — devi valutarla da più angolazioni per evitare trappole nascoste.

`evaluate_opportunity` risponde a questa domanda analizzando la posizione da **5 dimensioni indipendenti**:

1. **Pricing Edge (35%)** — Quanto vale di più questa posizione rispetto a quanto paghi? Se la compri a 2€ ma vale 2.5€, hai un margine di valore. Più grande è questo margine, meglio è.

2. **Risk/Reward (25%)** — Qual è il rapporto tra il massimo che puoi guadagnare e il massimo che puoi perdere? Un rapporto 10:2 (5:1) è buono; un rapporto 1:10 è cattivo.

3. **Breakeven Reachability (20%)** — A quante "mosse di mercato" (sigma) devi arrivare per toccare il break-even? Se il prezzo deve muoversi del 5% e solitamente si muove dell'1% al giorno, il breakeven è lontano e difficile da raggiungere. Se è vicino (< 1 sigma), è raggiungibile.

4. **Execution Cost (15%)** — Quanto ti costa comprare/vendere? Se il bid/ask spread è stretto (0%), è perfetto. Se è largo (15%), ti sottrae profitti subito all'apertura.

5. **Capital Efficiency (5%)** — Quanto guadagni dal tempo? Se theta (decadimento temporale) ti guadagna 0.1€ al giorno e il tuo rischio massimo è 1€, questo theta è prezioso.

Queste 5 dimensioni vengono **combinate con pesi diversi** (pricing edge è il più importante al 35%, efficienza di capitale è il meno importante al 5%) per produrre un **punteggio da 0 a 100**.

Il significato del punteggio:
- **80-100** → Eccellente, probabilmente vuoi aprire il trade
- **60-80** → Discreto, vale la pena monitorare ma non entrare yet
- **0-60** → Scadente, salta il trade

È come un "rating di qualità della posizione" prima di aprirla.

### Evaluation Dimensions

```python
@dataclass
class OpportunityEvaluation:
    # Dimensioni di valutazione (0-100)
    pricing_edge: float        # Fair value vs market (w=35%)
    risk_reward_ratio: float   # P&L max gain vs max loss (w=25%)
    breakeven_reachability: float  # % sigmas to BEP (w=20%)
    execution_cost: float      # Bid/Ask impact (w=15%)
    capital_efficiency: float  # Profit per $ rischiato (w=5%)

    # Score composito
    overall_score: float       # 0-100

    # Metadata
    recommendation: str        # "OPEN", "SKIP", "MONITOR"
    reasons: list[str]        # ["Edge too low", "Bid/Ask spread >15%", ...]

    # Thresholds
    passes_entry: bool         # score > 75?
    passes_risk: bool          # risk_per_contract < risk_available?
    passes_liquidity: bool     # bid_ask < 15%?
```

### Scoring Logica

```python
def evaluate_opportunity(
    pricing: PricingContext,
    entry_config: dict,
    risk_config: dict,
) -> OpportunityEvaluation:
    """
    Multi-dimensional valuation before opening trade
    """

    # 1. Pricing Edge (35%)
    # Fair value advantage vs market price
    edge_pct = (pricing.fair_value - pricing.market_price) / pricing.market_price * 100
    pricing_edge = score_edge(edge_pct)  # 0-100

    # 2. Risk/Reward Ratio (25%)
    # Max gain vs max loss for the strategy
    max_gain = strategy_max_gain(pricing)
    max_loss = strategy_max_loss(pricing)
    rr_ratio = max_gain / max_loss if max_loss > 0 else 0
    risk_reward = score_risk_reward(rr_ratio)  # 0-100

    # 3. Breakeven Reachability (20%)
    # Is BEP achievable based on historical volatility?
    move_1sigma = pricing.spot * row['rv_20'] * math.sqrt(pricing.dte_days/252)
    bep_distance_sigmas = (pricing.breakeven_distance * pricing.spot) / move_1sigma
    breakeven = score_bep_reachability(bep_distance_sigmas)  # 0-100

    # 4. Execution Cost (15%)
    # Bid/Ask spread impact on entry
    if pricing.bid_ask_pct > 0.15:  # > 15%
        execution_cost = 10  # Fail
    elif pricing.bid_ask_pct > 0.10:
        execution_cost = 50
    else:
        execution_cost = 100

    # 5. Capital Efficiency (5%)
    # Profit per $ rischiato (Sharpe-like)
    profit_per_dollar = max_gain / max_loss
    capital_eff = score_capital_efficiency(profit_per_dollar)  # 0-100

    # Composite score (weighted average)
    overall = (
        0.35 * pricing_edge +
        0.25 * risk_reward +
        0.20 * breakeven +
        0.15 * execution_cost +
        0.05 * capital_eff
    )

    # Decision logic
    reasons = []
    passes_entry = overall > 75
    passes_risk = check_risk_limits(max_loss, risk_config)
    passes_liquidity = pricing.bid_ask_pct < 0.15

    if pricing_edge < 20:
        reasons.append("Edge insufficiente (<20%)")
    if pricing.bid_ask_pct > 0.10:
        reasons.append(f"Bid/Ask spread alto ({pricing.bid_ask_pct:.1%})")
    if rr_ratio < 1.5:
        reasons.append(f"Risk/reward basso ({rr_ratio:.2f})")

    recommendation = (
        "OPEN" if (passes_entry and passes_risk and passes_liquidity)
        else "SKIP"
    )

    return OpportunityEvaluation(
        pricing_edge=pricing_edge,
        risk_reward_ratio=risk_reward,
        breakeven_reachability=breakeven,
        execution_cost=execution_cost,
        capital_efficiency=capital_eff,
        overall_score=overall,
        recommendation=recommendation,
        reasons=reasons,
        passes_entry=passes_entry,
        passes_risk=passes_risk,
        passes_liquidity=passes_liquidity,
    )
```

### Files
```
domain/decision/
├── opportunity_evaluator.py  (NEW)
│   ├── OpportunityEvaluation (dataclass)
│   ├── evaluate_opportunity(pricing, entry_config, risk_config)
│   ├── score_edge(edge_pct)
│   ├── score_risk_reward(ratio)
│   ├── score_bep_reachability(sigmas)
│   └── check_risk_limits(max_loss, config)
```

---

## Level 5: Trade Decision (Final Gate)

**Input**: OpportunityEvaluation
**Output**: TradeDecision (OPEN / SKIP / MONITOR)

### Final Decision Logic
```python
@dataclass
class TradeDecision:
    action: Literal["OPEN", "SKIP", "MONITOR"]
    reason: str
    size_contracts: int
    estimated_entry_price: float
    max_risk: float
    max_profit: float

    # Logging
    decision_log: dict  # All scores + reasons

def make_trade_decision(
    evaluation: OpportunityEvaluation,
    position_config: dict,
) -> TradeDecision:
    """
    Final gate before opening trade
    """

    # Reject if fails critical checks
    if not evaluation.passes_liquidity:
        return TradeDecision(
            action="SKIP",
            reason=f"Bid/Ask spread >15%: {evaluation.bid_ask_pct:.1%}",
            ...
        )

    if not evaluation.passes_risk:
        return TradeDecision(
            action="SKIP",
            reason=f"Risk exceeds limit: ${max_loss} > limit",
            ...
        )

    # Open if passes entry threshold
    if evaluation.passes_entry:
        # Calculate contract size based on risk allocation
        contracts = calculate_contracts(
            available_risk=position_config['available_risk'],
            risk_per_contract=evaluation.max_loss,
            size_multiplier=position_config['size_multiplier'],
        )

        return TradeDecision(
            action="OPEN",
            reason=f"Opportunity score {evaluation.overall_score:.0f}/100 exceeds threshold",
            size_contracts=contracts,
            ...
        )

    # Monitor if borderline (60-75 score)
    elif evaluation.overall_score > 60:
        return TradeDecision(
            action="MONITOR",
            reason=f"Score {evaluation.overall_score:.0f}/100 is borderline. Waiting for improvement",
            ...
        )

    # Skip if score too low
    else:
        return TradeDecision(
            action="SKIP",
            reason=f"Score {evaluation.overall_score:.0f}/100 below threshold (60). Reasons: {', '.join(evaluation.reasons)}",
            ...
        )
```

### Files
```
domain/decision/
├── trade_decision.py  (NEW)
│   ├── TradeDecision (dataclass)
│   └── make_trade_decision(evaluation, config) → TradeDecision
```

---

## Complete Decision Flow

```python
# In runs.py, durante backtest loop
def process_entry_signal(row: pd.Series, entry_config: dict, risk_config: dict):
    """
    Complete decision pipeline da segnali → trade decision
    """

    # Level 1: Classify zone
    zone = classify_zone(row['iv_rank'], row['adx'])
    logger.info(f"[L1] Zone: {zone}")

    # Level 2: Select strategy
    strategy_spec = select_strategy(
        zone=zone,
        trend=row['trend_signal'],
        squeeze_intensity=row['squeeze_intensity'],
        iv_rank=row['iv_rank'],
        entry_score=calculate_entry_score(row, entry_config),
    )
    logger.info(f"[L2] Strategy: {strategy_spec.name} (size_mult: {strategy_spec.size_multiplier:.0%})")

    if strategy_spec.name == "no_trade":
        return None

    # Level 3: Calculate pricing
    pricing = calculate_pricing(strategy_spec, row, entry_config)
    logger.info(f"[L3] Pricing: fair={pricing.fair_value:.2f}, market={pricing.market_price:.2f}, edge={pricing.edge:.1%}")

    # Level 4: Evaluate opportunity
    evaluation = evaluate_opportunity(pricing, entry_config, risk_config)
    logger.info(f"[L4] Opportunity: score={evaluation.overall_score:.0f}, edge={evaluation.pricing_edge:.0f}, rr={evaluation.risk_reward_ratio:.0f}")

    # Level 5: Make trade decision
    decision = make_trade_decision(evaluation, position_config)
    logger.info(f"[L5] Decision: {decision.action} - {decision.reason}")

    if decision.action == "OPEN":
        # Build position from strategy_spec.builder()
        position = strategy_spec.builder(
            date=row['date'],
            S=row['close'],
            iv=row['iv'],
            quantity=decision.size_contracts,
            ...
        )
        portfolio.open_position(position)

    return decision
```

---

## Architecture Files

```
domain/decision/  (NEW PACKAGE)
├── __init__.py
├── zone_classifier.py          # L1: Zone A/B/C/D
├── strategy_selector.py        # L2: Strategy selection matrix
├── pricing.py                  # L3: Fair value + Greeks
├── greeks_calculator.py        # L3: Helpers
├── opportunity_evaluator.py    # L4: Multi-dim scoring
├── trade_decision.py           # L5: Final gate
└── models.py                   # Dataclasses (Zone, PricingContext, etc)
```

**Total LOC**: ~800-1000 (spread across 6 files)

---

## Integration Points

1. **With selectors.py** → Move zone logic to zone_classifier.py, refactor select_strategy
2. **With entry_scoring.py** → Already provides entry_score (0-100)
3. **With strategy_builder.py** → Already provides builders
4. **With runs.py** → Call full decision pipeline instead of just select_strategy()
5. **With parameter_schema.py** → Add new config params (risk limits, opportunity thresholds)

---

## Configuration Parameters (New)

Add to `parameter_schema.py`:

```python
# Decision Layer
"decision.opportunity_threshold": {     # Score minimo per OPEN
    "type": "float",
    "min": 0.0, "max": 100.0,
    "default": "75",
    "unit": "value",
},
"decision.breakeven_threshold": {       # BEP reachability threshold
    "type": "float",
    "min": 0.5, "max": 3.0,
    "default": "1.5",
    "unit": "sigmas",
},
"decision.max_bid_ask_pct": {          # Max tolerable spread
    "type": "float",
    "min": 0.0, "max": 100.0,
    "default": "15",
    "unit": "pct",
},
"decision.rr_ratio_min": {             # Min risk/reward
    "type": "float",
    "min": 0.5, "max": 10.0,
    "default": "1.5",
    "unit": "ratio",
},

# Scoring weights
"opportunity.weight_edge": {"type": "float", "default": "0.35"},
"opportunity.weight_rr": {"type": "float", "default": "0.25"},
"opportunity.weight_bep": {"type": "float", "default": "0.20"},
"opportunity.weight_execution": {"type": "float", "default": "0.15"},
"opportunity.weight_efficiency": {"type": "float", "default": "0.05"},
```

---

## Testing Strategy

### Unit Tests
- test_zone_classifier: 4 zones + edge cases
- test_strategy_selector: Matrix logic for all zones
- test_pricing: All 13 strategies
- test_opportunity_evaluator: Scoring dimensions
- test_trade_decision: Decision logic

### Integration Tests
- test_full_pipeline: Segnali → decision
- test_entry_score_impact: Change entry_score → decision changes
- test_risk_limiting: Reject if max_loss > limit
- test_liquidity_filter: Reject if bid/ask > 15%

### Regression Tests
- Existing backtest results unchanged
- Size_multiplier applied correctly
- No infinite loops in decision logic

---

## Implementation Roadmap

### Week 1
- [ ] L1: Zone classifier
- [ ] L2: Strategy selector (matrix)

### Week 2
- [ ] L3: Pricing & Greeks
- [ ] L4: Opportunity evaluator

### Week 3
- [ ] L5: Trade decision
- [ ] Integration + tests

### Week 4
- [ ] Optimization (parameter tuning)
- [ ] Documentation

---

**Status**: Architecture designed, ready for implementation
**Next**: Begin with Zone Classifier (L1)
