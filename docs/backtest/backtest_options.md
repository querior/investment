# 📘 Backtest Options — Documento Unificato (Baseline Definitiva)

---

## 1. Obiettivo

Costruire un motore di backtest per strategie opzionali su ETF/indici con:

- pricing teorico (Black-Scholes)
- gestione greche
- strutture multi-leg (spread, butterfly)
- simulazione IV
- integrazione macro regime
- persistenza completa (snapshot + performance)
- analytics e visualizzazione
- evoluzione verso motore adattivo

**Target primario: IWM** (ETF su Russell 2000)
**Architettura multi-strumento:** configurazione per-instrument tramite `InstrumentConfig`

---

## 2. Architettura

### Layer

1. **Domain (runtime)**
    - `OptionLeg`
    - `Position`
    - `Portfolio`
2. **Persistence**
    - `BacktestRun`
    - `BacktestPosition`
    - `BacktestPositionSnapshot`
    - `BacktestPortfolioPerformance`
    - `BacktestPerformance`
    - `BacktestRunParameter`
3. **Engine**
    - loop giornaliero
    - update mercato
    - entry/exit
    - salvataggio snapshot
4. **Data preparation**
    - costruzione dataset (prezzi + IV + macro)

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

## 4. Configurazione per Strumento (InstrumentConfig)

Il motore è progettato per essere **portabile su qualsiasi indice/ETF** tramite un singolo oggetto di configurazione. Tutto il codice di pricing, EV e cost model riceve l'`InstrumentConfig` come dipendenza — nessun parametro hardcoded.

### Dataclass

```python
@dataclass
class InstrumentConfig:
    ticker: str
    dividend_yield: float        # q nel Black-Scholes
    iv_proxy: str                # "RVX" | "VIX" | "VXN" | "HV_simulated"
    iv_alpha: float              # downside boost nella formula HV simulata
    cost_model: CostModel
    contract_multiplier: int = 100
    settlement: str = "physical" # "physical" | "cash"
    iv_min: float = 0.10
    iv_max: float = 0.80
```

### Configurazioni predefinite

```python
IWM_CONFIG = InstrumentConfig(
    ticker="IWM",
    dividend_yield=0.015,
    iv_proxy="RVX",
    iv_alpha=4.0,
    cost_model=CostModel(commission_per_contract=0.65, bid_ask_spread_pct=0.02),
)

SPY_CONFIG = InstrumentConfig(
    ticker="SPY",
    dividend_yield=0.013,
    iv_proxy="VIX",
    iv_alpha=3.2,
    cost_model=CostModel(commission_per_contract=0.65, bid_ask_spread_pct=0.01),
)

QQQ_CONFIG = InstrumentConfig(
    ticker="QQQ",
    dividend_yield=0.006,
    iv_proxy="VXN",
    iv_alpha=4.5,
    cost_model=CostModel(commission_per_contract=0.65, bid_ask_spread_pct=0.015),
)

SPX_CONFIG = InstrumentConfig(
    ticker="SPX",
    dividend_yield=0.013,
    iv_proxy="VIX",
    iv_alpha=3.2,
    cost_model=CostModel(commission_per_contract=1.00, bid_ask_spread_pct=0.005),
    settlement="cash",
    # Attenzione: nozionale ~$550k per contratto — il sizing va adattato
)
```

### Tabella comparativa parametri

| Parametro | IWM | SPY | QQQ | SPX |
|---|---|---|---|---|
| Tipo opzione | Americana | Americana | Americana | **Europea** |
| Dividend yield (q) | 1.5% | 1.3% | 0.6% | 1.3% |
| IV media storica | 25–35% | 15–25% | 20–30% | 15–25% |
| IV proxy | RVX | VIX | VXN | VIX diretto |
| iv_alpha (HV sim.) | 4.0 | 3.2 | 4.5 | 3.2 |
| Commission/contratto | $0.65 | $0.65 | $0.65 | $1.00 |
| Bid-ask spread | 2% mid | 1% mid | 1.5% mid | 0.5% mid |
| Settlement | Fisico | Fisico | Fisico | **Cash** |
| Nozionale contratto | ~$20k | ~$55k | ~$48k | **~$550k** |
| Liquidità | Buona | Eccellente | Buona | Eccellente |

### Note per strumento

**IWM (target primario):** BS con `q=0.015` è approssimazione accettabile per validazione. Opzioni americane: early exercise trascurabile per short premium DTE 30-45.

**SPX (caso speciale):** opzioni europee → BS è esatto. VIX disponibile direttamente come IV. Nozionale elevato (~$550k) impone sizing dedicato — non comparabile agli ETF senza normalizzazione per notional.

**QQQ:** `iv_alpha` più alto perché il Nasdaq è più reattivo ai movimenti down. IV proxy VXN disponibile via CBOE.

**Architettura:** BS europeo con dividend yield continuo è l'approssimazione di riferimento per tutti gli strumenti nella fase di validazione con IV simulata.

### Uso nel motore

```python
# In runs.py — il config viene passato al motore al momento dell'inizializzazione
def run_backtest(run: BacktestRun, instrument: InstrumentConfig):
    ...
    trade_ev = compute_trade_ev(
        legs=strategy_spec.legs,
        S=row["close"],
        T=row["dte"] / 365,
        r=0.05,
        q=instrument.dividend_yield,
        sigma=row["iv"],
        cost_model=instrument.cost_model,
        multiplier=instrument.contract_multiplier,
    )
```

---

## 5. Simulazione IV

### Formula

$$
IV_t = \operatorname{clamp}\left(
1.15 \cdot \sqrt{252} \cdot \operatorname{std}(r_{t-19:t})
+ \alpha \cdot \max(0, -r_t),
\; iv_{\min}, \; iv_{\max}
\right)
$$

### Implementazione

```python
def enrich_with_iv(df, instrument: InstrumentConfig):
    """
    Arricchisce il dataframe con la colonna iv simulata.
    I parametri alpha, iv_min, iv_max vengono letti dall'InstrumentConfig.
    """
    df = df.sort_values("date").copy()

    log_ret = np.log(df["close"] / df["close"].shift(1))
    rv_20 = log_ret.rolling(20).std()

    downside_boost = instrument.iv_alpha * (-log_ret).clip(lower=0)
    iv = 1.15 * np.sqrt(252) * rv_20 + downside_boost

    df["iv"] = iv.clip(lower=instrument.iv_min, upper=instrument.iv_max)
    return df
```

### Note

- warmup necessario (~40–60 giorni)
- eseguita prima del backtest
- aggiunge solo la colonna `iv`
- questa formula è una proxy della HV, non dell'IV reale: non cattura il term structure né lo skew
- `iv_alpha` è specifico per strumento (vedi `InstrumentConfig`) — andrà calibrato su dati reali in fase beta

### Evoluzione prevista verso dati reali

- utilizzo diretto del proxy dedicato per strumento (`VIX`, `RVX`, `VXN`) come IV a 30gg
- **IV Rank / IV Percentile** per contestualizzazione storica
- **Term structure** (VIX9D, VIX, VIX3M, VIX6M)
- modelli **SABR** o **SVI** per fitting corretto dello skew

---

## 6. Fair Value (Black-Scholes)

### Implementazione

```python
from scipy.stats import norm
import numpy as np

def black_scholes(S, K, T, r, q, sigma, option_type="call"):
    """
    S     : prezzo sottostante
    K     : strike
    T     : anni alla scadenza (DTE/365)
    r     : tasso risk-free (es. 0.05)
    q     : dividend yield continuo — da InstrumentConfig.dividend_yield
    sigma : IV (simulata o reale)
    """
    if T <= 0:
        intrinsic = max(S - K, 0) if option_type == "call" else max(K - S, 0)
        return intrinsic

    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    if option_type == "call":
        price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)

    return price
```

---

## 7. Greche

### Implementazione

```python
def bs_greeks(S, K, T, r, q, sigma, option_type="call"):
    if T <= 0:
        return {"delta": 0, "gamma": 0, "theta": 0, "vega": 0, "prob_itm": 0}

    d1 = (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    delta = np.exp(-q * T) * norm.cdf(d1) if option_type == "call" \
            else -np.exp(-q * T) * norm.cdf(-d1)

    gamma = np.exp(-q * T) * norm.pdf(d1) / (S * sigma * np.sqrt(T))

    theta = (
        -S * np.exp(-q * T) * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
        - r * K * np.exp(-r * T) * norm.cdf(d2)
        + q * S * np.exp(-q * T) * norm.cdf(d1)
    ) / 365  # per-day

    vega = S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T) / 100  # per 1% IV move

    prob_itm = norm.cdf(d2) if option_type == "call" else norm.cdf(-d2)

    return {
        "delta": delta, "gamma": gamma,
        "theta": theta, "vega": vega,
        "prob_itm": prob_itm
    }
```

### Riferimento greche

| Greca | Significato | Uso nel modello |
|---|---|---|
| **Delta (Δ)** | Esposizione direzionale | Strike selection, delta breach exit |
| **Gamma (Γ)** | Variazione del Delta | Rischio accelerazione |
| **Theta (Θ)** | Decadimento temporale giornaliero | Theta decay exit rule |
| **Vega (ν)** | Sensibilità alla volatilità | IV spike exit rule |
| **Prob ITM** | N(d2) — probabilità esercizio | Calcolo PoP e EV |

---

## 8. Expected Value

### Dataclass

```python
@dataclass
class LegEV:
    strike: float
    option_type: str        # "call" / "put"
    position: str           # "long" / "short"
    quantity: int
    fair_value: float
    prob_itm: float
    delta: float

@dataclass
class TradeEV:
    legs: list[LegEV]
    net_premium: float           # credito netto incassato (+ = credito)
    max_profit: float            # credito netto per spread
    max_loss: float              # larghezza spread - credito
    prob_profit: float           # P(profit at expiry) — approssimata
    expected_value_gross: float
    transaction_costs: float
    expected_value_net: float

    @property
    def has_edge(self) -> bool:
        return self.expected_value_net > 0
```

### Calcolo

```python
def compute_trade_ev(
    legs: list[dict],        # [{strike, type, position, qty}]
    S, T, r, sigma,
    instrument: InstrumentConfig,
) -> TradeEV:

    q = instrument.dividend_yield
    multiplier = instrument.contract_multiplier
    cost_model = instrument.cost_model

    leg_evs = []
    net_premium = 0.0

    for leg in legs:
        fv = black_scholes(S, leg["strike"], T, r, q, sigma, leg["type"])
        greeks = bs_greeks(S, leg["strike"], T, r, q, sigma, leg["type"])

        sign = 1 if leg["position"] == "short" else -1
        net_premium += sign * fv * leg["qty"] * multiplier

        leg_evs.append(LegEV(
            strike=leg["strike"],
            option_type=leg["type"],
            position=leg["position"],
            quantity=leg["qty"],
            fair_value=fv,
            prob_itm=greeks["prob_itm"],
            delta=greeks["delta"]
        ))

    # Per spread: max_profit = credito, max_loss = spread_width - credito
    spread_width = abs(legs[1]["strike"] - legs[0]["strike"]) * multiplier
    max_profit = net_premium
    max_loss = spread_width - net_premium

    # PoP approssimata: prob che il sottostante resti fuori dallo short strike
    short_leg = next(l for l in leg_evs if l.position == "short")
    pop = 1 - short_leg.prob_itm  # per credit spread

    ev_gross = pop * max_profit - (1 - pop) * max_loss

    # Costi da CostModel dell'InstrumentConfig
    n_contracts = sum(l.quantity for l in leg_evs)
    costs = cost_model.total_cost(net_premium, n_contracts)

    ev_net = ev_gross - costs

    return TradeEV(
        legs=leg_evs,
        net_premium=net_premium,
        max_profit=max_profit,
        max_loss=max_loss,
        prob_profit=pop,
        expected_value_gross=ev_gross,
        transaction_costs=costs,
        expected_value_net=ev_net
    )
```

### Pipeline EV → Entry Decision

```
Fair Value BS
      ↓
Premium teorico vs. premio incassato
      ↓
Edge = (Premio - FV) / FV        ← filtro entry
      ↓
EV = PoP × profit_target - (1-PoP) × max_loss
      ↓
EV netto = EV - costi (comm. + slippage)
      ↓
Apri solo se EV_netto > soglia
```

---

## 9. Realismo Economico (CostModel)

`CostModel` è un campo di `InstrumentConfig` — ogni strumento ha i propri parametri di costo. Non esistono valori hardcoded nel codice di pricing.

### Implementazione

```python
@dataclass
class CostModel:
    commission_per_contract: float = 0.65
    min_commission: float = 1.00
    bid_ask_spread_pct: float = 0.02
    slippage_model: str = "fixed_pct"   # "fixed_pct" | "dynamic"

    def total_cost(self, premium: float, n_contracts: int) -> float:
        commission = max(
            n_contracts * self.commission_per_contract,
            self.min_commission
        )
        slippage = abs(premium) * self.bid_ask_spread_pct
        return commission + slippage

    def fill_price(self, mid_price: float, side: str) -> float:
        """Simula fill realistico: short → fill al bid, long → fill all'ask"""
        half_spread = mid_price * (self.bid_ask_spread_pct / 2)
        if side == "short":
            return mid_price - half_spread
        else:
            return mid_price + half_spread
```

### Parametri per strumento

| Voce | IWM | SPY | QQQ | SPX |
|---|---|---|---|---|
| Commission/contratto | $0.65 | $0.65 | $0.65 | $1.00 |
| Commissione minima | $1.00 | $1.00 | $1.00 | $1.00 |
| Bid-ask spread | 2% mid | 1% mid | 1.5% mid | 0.5% mid |
| Modello slippage | fixed_pct | fixed_pct | fixed_pct | fixed_pct |

---

## 10. Integrazione Entry Logic

Il punto di innesto è **prima dell'apertura della posizione** in `runs.py`. L'`InstrumentConfig` viene passato al motore all'inizializzazione e propagato a ogni chiamata di pricing.

```python
def run_backtest(run: BacktestRun, instrument: InstrumentConfig):
    ...

def try_open_position(row, strategy_spec, portfolio, instrument: InstrumentConfig):

    trade_ev = compute_trade_ev(
        legs=strategy_spec.legs,
        S=row["close"],
        T=row["dte"] / 365,
        r=0.05,
        sigma=row["iv"],
        instrument=instrument,
    )

    # Filtro EV — apri solo se ha edge netto
    if not trade_ev.has_edge:
        return None

    # Salva EV sull'apertura per analytics post-trade
    position = strategy_spec.builder(row)
    position.entry_ev = trade_ev

    return position
```

### Campi da aggiungere a BacktestPosition

Per persistere l'EV al momento dell'apertura:

| Campo | Tipo | Descrizione |
|---|---|---|
| `entry_fair_value` | float | Fair value BS aggregato al momento dell'apertura |
| `entry_ev_gross` | float | EV lordo stimato pre-trade |
| `entry_ev_net` | float | EV netto dopo costi |
| `entry_prob_profit` | float | PoP stimata all'apertura |
| `entry_transaction_costs` | float | Costi totali stimati |

---

## 11. P&L Model

### Definizioni

- **Realized PnL** → posizioni chiuse
- **Unrealized PnL** → posizioni aperte
- **Total PnL** → somma

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

## 12. Performance Tracking

### BacktestPerformance

- `nav`
- `period_return`

```python
period_return = (nav_t / nav_{t-1}) - 1
```

### BacktestRun (metriche aggregate)

- CAGR
- Volatility
- Sharpe
- Max Drawdown
- Win Rate
- Profit Factor
- N trades

### Analytics Post-Trade (nuove metriche EV)

| Metrica | Formula | Utilizzo |
|---|---|---|
| **EV accuracy** | EV_stimato vs P&L_realizzato | Calibrazione modello |
| **Edge realizzato** | media(P&L) / media(EV_stimato) | Validazione edge |
| **Cost drag** | media(transaction_costs) / media(max_profit) | Impatto costi |
| **PoP accuracy** | win_rate_reale vs prob_profit_stimata | Calibrazione IV |

---

## 13. Strategy Engine

### StrategySpec

```python
@dataclass
class StrategySpec:
    name: str
    builder: Optional[Callable[..., Position]]
    should_trade: bool = True
```

### Strategie implementate

- bull_put_spread
- bear_call_spread
- put_broken_wing_butterfly (neutral)

### Esempio builder

```python
def create_bear_call_spread(...):
    short_strike = S * 1.05
    long_strike = S * 1.08
```

> ⚠️ **Da evolvere:** gli strike vanno scelti per **Delta target** (es. short a 0.16Δ, long a 0.05Δ) invece di moltiplicatori fissi, per adattarsi al regime di volatilità corrente.

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

## 14. Macro Integration

### Funzione

```python
def compute_macro_risk_score(db, date):
```

### Logica

- expansion → +1
- neutral → 0
- contraction → -1

### Classificazione

- ≥ 0.5 → RISK_ON
- ≤ -0.5 → RISK_OFF
- else → NEUTRAL

### Uso

```python
_, macro_regime = compute_macro_risk_score(db, date)
strategy = select_strategy(iv, macro_regime)
```

---

## 15. Parametrizzazione

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

## 16. Warmup Period

```python
load_start = run.start_date - timedelta(days=40)
df = df[df["date"] >= run.start_date]
```

---

## 17. Analytics API

### Lista posizioni

```
GET /runs/{run_id}/positions
```

Include:

- metadata
- realized_pnl
- performance_pct
- days_in_trade
- latest snapshot (opzionale)
- **entry_ev_net** (nuovo)
- **entry_prob_profit** (nuovo)

### History posizione

```
GET /runs/{run_id}/positions/{position_id}/history
```

Include:

- header posizione
- serie temporale snapshot

---

## 18. Visualizzazione

### Layout

```
[ underlying vs position ]
[ pnl vs iv             ]
```

### Grafico 1

- underlying_price
- position_price

### Grafico 2

- position_pnl
- iv

### Caratteristiche

- asse X condiviso
- doppio asse Y
- sincronizzazione

---

## 19. Exit Engine

### Architettura

`should_close_position` rimossa da `strategy_builder.py`. La logica vive interamente in `exit_rules.py`, chiamata direttamente da `runs.py` tramite `ExitContext`.

### ExitContext

```python
@dataclass
class ExitContext:
    position: Position
    row: pd.Series                  # indicatori di mercato correnti
    snapshot: Optional[object]      # ultime greche persistite
    entry_row: Optional[pd.Series]  # contesto al momento dell'apertura
```

### Pipeline di regole con priorità

```python
EXIT_RULES: list[ExitRule] = [
    rule_dte,
    rule_profit_target,
]

def should_close(ctx: ExitContext) -> bool:
    return any(rule(ctx) for rule in EXIT_RULES)
```

L'ordine della lista definisce la priorità implicita. In futuro `any` può essere sostituito con scoring weighted (ML-ready).

### Struttura file

```
domain/strategy/
├── strategy_builder.py    # builders
├── selectors.py           # entry selection
├── exit_context.py        # ExitContext dataclass ✅
├── exit_rules.py          # regole di exit modulari ✅
```

### Regole — Stato attuale

| Regola | Segnale | Attiva |
|---|---|---|
| `rule_dte` | DTE <= 21 | ✅ |
| `rule_profit_target` | profitto >= 50% credito | ✅ |
| `rule_stop_loss` | perdita > 200% credito | ✅ |
| `rule_macro_reversal` | regime opposto alla strategia | ✅ |
| `rule_momentum_reversal` | RSI + MACD in direzione opposta | ✅ |
| `rule_trailing_stop` | profitto max >= 30% poi < 15% | — |
| `rule_iv_spike` | iv_rv_ratio > 2.0 | — |
| `rule_delta_breach` | delta fuori range tolleranza | — |
| `rule_theta_decay` | theta decay accelerato | — |

---

### Configurazione regole di uscita (spec)

Ogni regola deve diventare configurabile per run tramite `BacktestRunParameter`.
La configurazione viene costruita in `runs.py` e passata a `ExitContext.exit_config`.
Ogni regola legge la propria configurazione dal contesto invece di usare soglie hardcoded.

#### Struttura ExitContext aggiornata

```python
@dataclass
class ExitContext:
    position: Position
    row: pd.Series
    snapshot: Optional[object]
    entry_row: Optional[pd.Series]
    exit_config: dict = field(default_factory=dict)  # da aggiungere
```

#### Schema configurazione per regola

```json
{
  "rule_dte": {
    "enabled": true,
    "threshold_days": 21
  },
  "rule_profit_target": {
    "enabled": true,
    "threshold_pct": 50
  },
  "rule_stop_loss": {
    "enabled": true,
    "threshold_pct": 200
  },
  "rule_trailing_stop": {
    "enabled": false,
    "min_profit_pct": 30,
    "pullback_pct": 15
  },
  "rule_macro_reversal": {
    "enabled": true
  },
  "rule_momentum_reversal": {
    "enabled": true,
    "rsi_threshold": 30,
    "use_macd": true
  },
  "rule_iv_spike": {
    "enabled": false,
    "threshold_ratio": 2.0
  },
  "rule_delta_breach": {
    "enabled": false,
    "threshold": 0.50
  },
  "rule_theta_decay": {
    "enabled": false,
    "threshold_ratio": 0.05
  }
}
```

#### Mapping BacktestRunParameter → exit_config

I parametri vengono salvati come `BacktestRunParameter` con chiavi nel formato
`exit.<regola>.<campo>`. Esempi:

| key | value | unit |
|---|---|---|
| `exit.rule_stop_loss.enabled` | `true` | bool |
| `exit.rule_stop_loss.threshold_pct` | `150` | pct |
| `exit.rule_profit_target.threshold_pct` | `50` | pct |
| `exit.rule_dte.threshold_days` | `21` | days |
| `exit.rule_trailing_stop.enabled` | `false` | bool |
| `exit.rule_trailing_stop.min_profit_pct` | `30` | pct |
| `exit.rule_trailing_stop.pullback_pct` | `15` | pct |
| `exit.rule_momentum_reversal.rsi_threshold` | `30` | value |
| `exit.rule_iv_spike.threshold_ratio` | `2.0` | value |
| `exit.rule_delta_breach.threshold` | `0.50` | value |

Se un parametro non è presente si applica il default indicato nello schema.

#### Logica `should_close` con config

```python
ALL_RULES = [
    rule_dte, rule_profit_target, rule_stop_loss, rule_trailing_stop,
    rule_macro_reversal, rule_momentum_reversal,
    rule_iv_spike, rule_delta_breach, rule_theta_decay,
]

def should_close(ctx: ExitContext) -> tuple[bool, dict | None]:
    for rule in ALL_RULES:
        if rule(ctx):   # ogni regola controlla internamente enabled
            ...
```

Ogni regola usa un helper `_cfg(ctx, rule_name)` per leggere la propria configurazione
con fallback ai default:

```python
def _cfg(ctx: ExitContext, rule: str) -> dict:
    return ctx.exit_config.get(rule, {})

def rule_stop_loss(ctx: ExitContext) -> bool:
    cfg = _cfg(ctx, "rule_stop_loss")
    if not cfg.get("enabled", True):
        return False
    threshold = float(cfg.get("threshold_pct", 200)) / 100
    pnl = ctx.position.price - ctx.position.initial_value
    return ctx.position.initial_value < 0 and pnl <= -abs(ctx.position.initial_value) * threshold
```

#### Costruzione exit_config in runs.py

```python
def _build_exit_config(params_dict: dict) -> dict:
    def _get(key, default):
        p = params_dict.get(key)
        return p["value"] if p else default

    return {
        "rule_dte": {
            "enabled": _get("exit.rule_dte.enabled", "true").lower() == "true",
            "threshold_days": int(_get("exit.rule_dte.threshold_days", "21")),
        },
        "rule_profit_target": {
            "enabled": _get("exit.rule_profit_target.enabled", "true").lower() == "true",
            "threshold_pct": float(_get("exit.rule_profit_target.threshold_pct", "50")),
        },
        "rule_stop_loss": {
            "enabled": _get("exit.rule_stop_loss.enabled", "true").lower() == "true",
            "threshold_pct": float(_get("exit.rule_stop_loss.threshold_pct", "200")),
        },
        "rule_trailing_stop": {
            "enabled": _get("exit.rule_trailing_stop.enabled", "false").lower() == "true",
            "min_profit_pct": float(_get("exit.rule_trailing_stop.min_profit_pct", "30")),
            "pullback_pct": float(_get("exit.rule_trailing_stop.pullback_pct", "15")),
        },
        "rule_macro_reversal": {
            "enabled": _get("exit.rule_macro_reversal.enabled", "true").lower() == "true",
        },
        "rule_momentum_reversal": {
            "enabled": _get("exit.rule_momentum_reversal.enabled", "true").lower() == "true",
            "rsi_threshold": float(_get("exit.rule_momentum_reversal.rsi_threshold", "30")),
            "use_macd": _get("exit.rule_momentum_reversal.use_macd", "true").lower() == "true",
        },
        "rule_iv_spike": {
            "enabled": _get("exit.rule_iv_spike.enabled", "false").lower() == "true",
            "threshold_ratio": float(_get("exit.rule_iv_spike.threshold_ratio", "2.0")),
        },
        "rule_delta_breach": {
            "enabled": _get("exit.rule_delta_breach.enabled", "false").lower() == "true",
            "threshold": float(_get("exit.rule_delta_breach.threshold", "0.50")),
        },
        "rule_theta_decay": {
            "enabled": _get("exit.rule_theta_decay.enabled", "false").lower() == "true",
            "threshold_ratio": float(_get("exit.rule_theta_decay.threshold_ratio", "0.05")),
        },
    }
```

---

## 20. Stato Attuale

Sistema supporta:

- IV simulata (proxy HV con downside boost, parametrizzata per strumento)
- `InstrumentConfig` — entity su DB, configurazione per-strumento ✅
- `CostModel` — commissioni + slippage per-strumento ✅
- Fair Value Black-Scholes con dividend yield `q` per ogni leg ✅
- Greche complete inclusa `prob_itm` ✅
- Expected Value pre-trade (`compute_trade_ev`) ✅
- Filtro entry su `is_credit` (credito netto positivo) ✅
- Persistenza EV su `BacktestPosition` (ev_gross, ev_net, prob_profit, transaction_costs, fair_value) ✅
- PnL completo (realized + unrealized + total) ✅
- Multi-strategy engine ✅
- Macro integration ✅
- Tracking storico ✅
- Base analytics ✅
- `rule_stop_loss` attiva (200% credito) ✅

---

## 21. Roadmap

### Fase 1 — InstrumentConfig + Fair Value + EV + Realismo Economico ✅ COMPLETATA

| Step | Descrizione | Stato |
|---|---|---|
| 1.0 | `InstrumentConfig` (entity DB) + `CostModel` | ✅ |
| 1.1 | `black_scholes()` con `q` da InstrumentConfig | ✅ |
| 1.2 | `bs_greeks()` con `prob_itm` | ✅ |
| 1.3 | `compute_trade_ev()` con InstrumentConfig | ✅ |
| 1.4 | Filtro entry su `is_credit` (has_edge rimandato a Fase 4 con IV reale) | ✅ |
| 1.5 | Persistenza EV su `BacktestPosition` | ✅ |
| 1.6 | `rule_stop_loss` attiva | ✅ |
| 1.7 | Metriche EV accuracy in analytics | Da fare |

### Fase 2 — Calibrazione Risk Management

Priorità alta: correggere le asimmetrie di rischio emerse dall'analisi critica prima di
procedere con entry logic avanzata.

| Step | Descrizione |
|---|---|
| 2.1 | Abbassare stop loss da 200% a 150% del credito |
| 2.2 | `entry_row` in ExitContext per contesto relativo all'entry |
| 2.3 | Attivare `rule_trailing_stop` (con entry_row disponibile) |
| 2.4 | Gestione regime NEUTRAL in exit: non aprire nuove posizioni se macro = NEUTRAL |
| 2.5 | `rule_delta_breach` attiva (usa snapshot greche già persistiti) |

### Fase 3 — Strike Selection per Delta Target

Modifica strutturale alla costruzione delle posizioni. Sostituisce i moltiplicatori fissi
con strike scelti per delta target, rendendo la PoP stabile al variare di IV.

| Step | Descrizione |
|---|---|
| 3.1 | Funzione `find_strike_by_delta(S, T, r, q, sigma, target_delta, option_type)` |
| 3.2 | Bull put spread: short a 0.16Δ, long a 0.05Δ |
| 3.3 | Bear call spread: short a 0.16Δ, long a 0.05Δ |
| 3.4 | Broken wing butterfly: ricalibrare con delta target |
| 3.5 | Aggiornare `compute_trade_ev` per usare gli strike da delta (già compatibile) |

### Fase 4 — Entry Logic Avanzata

| Step | Descrizione |
|---|---|
| 4.1 | Soglia IV minima assoluta in entry (es. IV > 0.15 per evitare premi irrisori) |
| 4.2 | IV Rank / IV Percentile su finestra storica (> 30° percentile) |
| 4.3 | RSI come filtro conferma in entry (non solo in exit) |
| 4.4 | MACD histogram come filtro direzionale in entry |
| 4.5 | Usare `trend_signal` (già calcolato con dead zone ±1%) al posto di `ema > sma` |
| 4.6 | Neutral strategy: aggiungere filtro IV minima e macro non RISK_OFF |
| 4.7 | Multi-factor scoring entry (combinazione ponderata dei filtri) |

### Fase 5 — IV Realistica

Con IV reale il filtro `has_edge` diventa significativo.

| Step | Descrizione |
|---|---|
| 5.1 | VIX / RVX diretto come IV a 30gg |
| 5.2 | IV Rank / IV Percentile su storia reale |
| 5.3 | Term structure semplificata (VIX9D, VIX, VIX3M) |
| 5.4 | Attivare `has_edge` come filtro primario di entry |
| 5.5 | Introduzione dati IV storici reali (OptionsDX, CBOE) |

### Fase 6 — Motore Adattivo

| Step | Descrizione |
|---|---|
| 6.1 | Rule-based avanzato (multi-factor scoring) |
| 6.2 | Regime detection automatico per aggiustamento parametri |
| 6.3 | Machine learning |
| 6.4 | Reinforcement learning |

---

## 22. Stato Maturità

Sistema evoluto da:

- prototipo statico

a:

- motore di backtest **dinamico, multi-strategy, macro-aware, multi-instrument, estendibile**

Prossimo obiettivo: elevare a livello **beta** con `InstrumentConfig`, Fair Value, EV e realismo economico integrati.

---

## 23. Analisi Critica — Strategie e Segnali

Valutazione qualitativa emersa dall'analisi del backtest in esecuzione (aprile 2026).
Serve da riferimento per le priorità di sviluppo delle fasi 2–4.

---

### 23.1 Entry Logic

#### Bull Put Spread (`RISK_ON + trend UP + iv_rv_ratio > 1.1`)

La combinazione macro + trend ha senso concettuale: vendi puts in un contesto rialzista
con supporto macro. Tuttavia:

- `iv_rv_ratio > 1.1` è un filtro quasi sempre soddisfatto con IV simulata. La formula
  `IV = 1.15 * √252 * rv_20 + α * downside_boost` costruisce strutturalmente IV > RV.
  Il filtro non discrimina i momenti buoni da quelli cattivi — è sostanzialmente inerte
  con IV simulata.
- RSI e MACD sono calcolati nel dataset ma non usati in entry. Si entra anche quando
  il momentum è già in deterioramento — solo il trend di lungo periodo filtra.
- `trend_signal` (segnale derivato con dead zone ±1%) è calcolato ma ignorato.
  Il selector usa direttamente `ema_20 > sma_50` senza soglia, quindi entra anche
  con trend marginale.

#### Bear Call Spread (`RISK_OFF + trend DOWN + iv_rv_ratio > 1.1`)

Stesso problema simmetrico, con una vulnerabilità aggiuntiva: nei periodi RISK_OFF
i mercati possono avere violenti rimbalzi tecnici (short squeeze, pivot di policy).
Il short call a 1.05×S è esposto a questi eventi prima che la exit logic intervenga.

#### Neutral Broken Wing Butterfly (`|EMA - SMA| / price < 0.01`)

Entra quando non c'è trend chiaro, ma senza alcuna condizione di volatilità.
La strategia viene aperta indifferentemente con IV al 12% (premi minimi, non vale
il rischio) o al 40% (rischio strutturale elevato). La broken wing ha payoff asimmetrico
— perdita massima sul lato downside più alta che sull'upside — entrarla durante
stress di mercato è problematico.

---

### 23.2 Strike Selection — Problema Strutturale

Gli strike sono fissi in termini percentuali su S. Il 5% OTM non ha lo stesso
significato probabilistico al variare di IV:

| IV | Delta del put a 0.95×S (DTE=45) | Prob. perdita |
|---|---|---|
| 15% | ~0.10 Δ | bassa |
| 25% | ~0.22 Δ | media |
| 40% | ~0.35 Δ | alta |

Nelle fasi di stress (IV alta, spesso coincidente con RISK_OFF), gli strike si
avvicinano in termini probabilistici. Le posizioni aperte nei momenti di maggiore
rischio sono anche quelle con PoP più bassa — l'inverso dell'obiettivo.

**Fix: strike selection per Delta target (0.16Δ short, 0.05Δ long).**
Con delta target la PoP è stabile ~84% indipendentemente dal regime di volatilità.

---

### 23.3 Exit Logic — Timing e Soglie

#### Stop loss a 200% del credito

Con profit target a 50% e stop a 200%, il break-even richiede ~80% win rate:

```
win_rate × 50 = (1 - win_rate) × 200  →  win_rate = 80%
```

È una soglia generosa che amplifica le perdite quando la strategia va contro.
Valori tipici nel premium selling sono 100–150%. Abbassare a 150% riduce il
requisito di win rate al ~75%.

#### rule_momentum_reversal (RSI < 30 AND macd < 0 per bull put)

RSI < 30 indica oversold — il mercato ha già venduto forte. A questo punto il bull
put spread è già in difficoltà. L'exit è corretta come protezione ma è un segnale
laggard: interviene quando il danno è già parzialmente fatto. Potrebbe essere più
utile in entry (non aprire bull put con RSI < 40) che in exit.

#### Regime NEUTRAL non attiva exit

Una bull put aperta in RISK_ON rimane aperta attraverso periodi neutrali finché
non arriva RISK_OFF o DTE. Con il macro score mensile questo può significare
settimane di esposizione in contesto deteriorato.

---

### 23.4 Segnali Calcolati ma Non Utilizzati in Entry

| Segnale | Usato in entry | Usato in exit | Note |
|---|---|---|---|
| `rsi_14` | No | Sì (momentum_reversal) | Utile come filtro entry |
| `macd` | No | Sì (momentum_reversal) | Utile come conferma direzionale |
| `macd_hist` | No | No | Segno del histogram indica momentum |
| `trend_signal` | No | No | Già ha dead zone ±1%, sostituisce `ema > sma` |
| `rv_20` | Indirettamente | No | Soglia assoluta IV > RV × 1.2 più robusta |

---

### 23.5 Disallineamento Temporale Macro/Tecnico

Il `macro_regime` è derivato da indicatori mensili (FRED). Il trend tecnico (EMA/SMA)
è giornaliero. La condizione di entry richiede entrambi, ma il macro convalida su scala
mensile mentre il trend può invertirsi in pochi giorni. Si può entrare in un bull put
spread con macro RISK_ON ma trend tecnico in virata, perché il selector guarda solo
`ema_20 > sma_50` istantaneamente.

---

### 23.6 Priorità di Intervento

| Priorità | Problema | Impatto atteso |
|---|---|---|
| 1 | Strike fissi → PoP variabile con IV | Alto — riduce perdite in alta volatilità |
| 2 | Stop loss 200% → R:R sfavorevole | Alto — capita le perdite massime |
| 3 | IV filter inerte con IV simulata | Medio — non migliora finché IV è simulata |
| 4 | Neutral strategy senza filtro IV | Medio — evita entries in contesti sfavorevoli |
| 5 | RSI/MACD non usati in entry | Medio — migliorano timing di apertura |
| 6 | Macro NEUTRAL non attiva exit | Basso — effetto marginale sulla serie storica |

---

## 24. Scaletta Implementazione — Revisione Post-Analisi

Ordine raccomandato basato sull'analisi critica. Ogni step è indipendente e testabile
prima di procedere al successivo.

---

### Step 1 — Exit rules configurabili da interfaccia

I parametri di ogni regola di uscita (enabled, soglie) vengono definiti dall'utente
nel form di configurazione del run, salvati come `BacktestRunParameter` e letti
a runtime. Nessun valore hardcoded nel codice.

**Backend:**
- `ExitContext` aggiunge `exit_config: dict`
- `exit_rules.py` — ogni regola legge `enabled` e soglie da `ctx.exit_config`;
  `EXIT_RULES` diventa `ALL_RULES` (tutte le regole sempre considerate,
  ognuna si auto-abilita/disabilita dal config)
- `runs.py` — `_build_exit_config(params_dict)` costruisce il config dai
  `BacktestRunParameter` con la convenzione `exit.<regola>.<campo>`
  e lo inietta nell'`ExitContext` ad ogni iterazione

**Frontend:**
- Sezione "Exit Rules" nel form di configurazione del run
- Per ogni regola: toggle enabled/disabled + input per le soglie
- I valori vengono salvati come `BacktestRunParameter` al salvataggio del run

---

### Step 2 — Strike selection per Delta target

Funzione `find_strike_by_delta(S, T, r, q, sigma, target_delta, option_type)` che
risolve per K usando ricerca numerica (bisezione su delta BS). I builders ricevono
`target_delta_short` e `target_delta_long` come parametri (configurabili da
`BacktestRunParameter`). Valori default: short a 0.16Δ, long a 0.05Δ.

Questo è il fix a maggiore impatto sul P&L. Rende la PoP stabile al variare
del regime di volatilità.

---

### Step 3 — Filtri entry rafforzati

In ordine di implementazione:

1. Sostituire `ema_20 > sma_50` con `trend_signal == 1` (o `== -1`) nel selector —
   già calcolato, una riga di cambiamento.
2. Aggiungere soglia IV minima assoluta: non aprire posizioni con IV < 0.18
   (premi troppo bassi per compensare il rischio).
3. Aggiungere filtro RSI in entry: non aprire bull put se RSI < 40
   (momentum già deteriorato).
4. Neutral strategy: aggiungere condizione `IV > 0.15 and macro != "RISK_OFF"`.

Tutti i valori soglia configurabili da `BacktestRunParameter`.

---

### Step 4 — Metriche EV accuracy (analytics post-trade)

Confronto tra `entry_ev_net` (stimato) e `realized_pnl` per ogni posizione chiusa.
Calcolare per l'intero run: EV accuracy, edge realizzato, cost drag, PoP accuracy.
Da esporre nelle API analytics e nella UI.

---

### Step 5 — IV Realistica (VIX / RVX)

Sostituire IV simulata con VIX/RVX come proxy IV a 30gg. Prerequisito per
attivare `has_edge` come filtro entry significativo. Sblocca anche IV Rank /
IV Percentile per un filtro volatilità robusto.

---

# 📘 Appendice — Backtest UI (Interattività e Analisi)

---

## 📊 Backtest UI — Prossimi Step

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
- **entry_ev_net** (nuovo)
- **entry_prob_profit** (nuovo)
- **entry_transaction_costs** (nuovo)

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
    - **ev_net** (nuovo)
    - **pop** (nuovo)

---

## 7. Analisi avanzata (step successivo)

Opzionale:

- terzo grafico:
    - delta
    - gamma
    - theta
    - vega
- toggle "advanced view"
- **grafico EV stimato vs P&L realizzato** (nuovo — per validazione modello)

---

## 8. Realismo economico

Da introdurre dopo UI stabile:

- commissioni
- slippage

👉 impatta direttamente i grafici PnL

---

## 📌 Ordine di implementazione consigliato

1. Fair Value + EV + CostModel (backend)
2. Persistenza EV su BacktestPosition
3. tooltip sincronizzato
4. marker apertura/chiusura
5. zoom + brush
6. click tabella → dettaglio posizione
7. filtri lista posizioni (incluso EV/PoP)
8. pannello metadati (inclusi campi EV)
9. commissioni/slippage attivi
10. greche opzionali
11. grafico EV vs P&L realizzato

---

## 🎯 Obiettivo

Passare da:

- visualizzazione statica

a:

- **strumento interattivo di analisi trading** con Fair Value, Expected Value e realismo economico integrati
