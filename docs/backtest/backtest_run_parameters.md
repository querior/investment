# BacktestRunParameter — Parametri di Configurazione

Ogni `BacktestRun` può avere parametri specifici via `BacktestRunParameter` (tabella: `key`, `value`, `unit`).

I parametri vengono letti in fase di esecuzione con fallback a default se non presenti.

---

## Parametri di Pipeline

Gestiti in `data_preparation/pipeline.py`

### Volatilità e IV (TIER 1 CRITICAL)

| Key | Type | Default | Descrizione | Usato da |
|-----|------|---------|-------------|----------|
| `alpha_volatility` | float | 4.0 | Alpha nel calcolo IV (formula: RV + alpha × jump) | `enrich_with_iv()` |
| `iv_min` | float | 0.10 | Minimo IV clip | `enrich_with_iv()` |
| `iv_max` | float | 0.80 | Massimo IV clip | `enrich_with_iv()` |
| `iv_rank.lookback_days` | int | 252 | Finestra rolling per IV Rank (52 settimane) | `add_iv_rank_and_percentile()` |

### Trend e Forza Trend (TIER 1 CRITICAL)

| Key | Type | Default | Descrizione | Usato da |
|-----|------|---------|-------------|----------|
| `adx.period` | int | 14 | Periodo ADX | `add_adx()` |

### Squeeze e Volume (TIER 2 MEDIA)

| Key | Type | Default | Descrizione | Usato da |
|-----|------|---------|-------------|----------|
| `squeeze.bb_percentile` | int | 20 | Percentile Bollinger Bands per squeeze (0-100) | `add_ttm_squeeze()` |
| `squeeze.macd_threshold` | float | 0.5 | Soglia MACD flatness per squeeze | `add_ttm_squeeze()` |
| `volume.sma_period` | int | 20 | Periodo SMA del volume | `add_volume_metrics()` |

---

## Parametri di Esecuzione (EOD Backtest)

Gestiti in `runs.py`

### Capitale e Trading

| Key | Type | Default | Descrizione | Usato da |
|-----|------|---------|-------------|----------|
| `symbol` | string | — | Ticker del sottostante (es. "IWM", "SPY") | `prepare_market_df()` |
| `initial_capital` | float | 0.0 | Capitale iniziale | `run_eod_backtest()` |
| `entry_every_n_days` | int | 30 | Frequenza di entry (ogni N giorni) | `run_eod_backtest()` |
| `ticker` | string | "IWM" | Ticker per configurazione strumenti | `get_instrument_config()` |

### Strategy Selection

| Key | Type | Default | Descrizione | Usato da |
|-----|------|---------|-------------|----------|
| `entry.target_delta_short` | float | — | Delta target per short leg opzioni | `select_strategy()` |
| `entry.target_delta_long` | float | — | Delta target per long leg opzioni | `select_strategy()` |
| `entry.iv_min_threshold` | float | 0.18 | IV minimo per entry | `_build_entry_config()` |
| `entry.rsi_min_bull` | float | 40 | RSI minimo trend rialzista | `_build_entry_config()` |
| `entry.iv_min_neutral` | float | 0.15 | IV minimo neutrale | `_build_entry_config()` |
| `entry.iv_rv_ratio_min` | float | 1.1 | IV/RV ratio minimo | `_build_entry_config()` |

### Exit Rules (TIER 2+)

| Key | Type | Default | Descrizione | Usato da |
|-----|------|---------|-------------|----------|
| `exit.rule_dte.enabled` | bool | true | Abilita exit su DTE minimo | `_build_exit_config()` |
| `exit.rule_dte.threshold_days` | float | 21 | Giorni minimi DTE | `_build_exit_config()` |
| `exit.rule_profit_target.enabled` | bool | true | Abilita exit profit target | `_build_exit_config()` |
| `exit.rule_profit_target.threshold_pct` | float | 50 | Profit target % | `_build_exit_config()` |
| `exit.rule_stop_loss.enabled` | bool | true | Abilita exit stop loss | `_build_exit_config()` |
| `exit.rule_stop_loss.threshold_pct` | float | 200 | Stop loss % | `_build_exit_config()` |
| `exit.rule_trailing_stop.enabled` | bool | false | Abilita trailing stop | `_build_exit_config()` |
| `exit.rule_trailing_stop.min_profit_pct` | float | 30 | Profit min prima trailing | `_build_exit_config()` |
| `exit.rule_trailing_stop.pullback_pct` | float | 15 | Pullback % trailing | `_build_exit_config()` |
| `exit.rule_macro_reversal.enabled` | bool | true | Abilita exit su cambio regime | `_build_exit_config()` |
| `exit.rule_momentum_reversal.enabled` | bool | true | Abilita exit su momentum | `_build_exit_config()` |
| `exit.rule_momentum_reversal.rsi_threshold` | float | 30 | RSI soglia momentum | `_build_exit_config()` |
| `exit.rule_momentum_reversal.use_macd` | bool | true | Usa MACD in momentum check | `_build_exit_config()` |
| `exit.rule_iv_spike.enabled` | bool | false | Abilita exit su IV spike | `_build_exit_config()` |
| `exit.rule_iv_spike.threshold_ratio` | float | 2.0 | IV spike ratio | `_build_exit_config()` |
| `exit.rule_delta_breach.enabled` | bool | false | Abilita exit su delta breach | `_build_exit_config()` |
| `exit.rule_delta_breach.threshold` | float | 0.50 | Delta breach soglia | `_build_exit_config()` |
| `exit.rule_theta_decay.enabled` | bool | false | Abilita exit su theta decay | `_build_exit_config()` |
| `exit.rule_theta_decay.threshold_ratio` | float | 0.05 | Theta decay ratio | `_build_exit_config()` |

---

## Parametri EOM Backtest

Gestiti in `runs.py` — `execute_eom_backtest()`

| Key | Type | Default | Descrizione | Usato da |
|-----|------|---------|-------------|----------|
| `coherence.factor` | float | 0.5 | Intensità riduzione per pillar neutral | `get_allocation_parameter()` |
| `allocation.alpha` | float | 0.3 | Alpha smoothing allocazione mensile | `compute_effective_allocation()` |
| `initial_allocation` | string | "neutral" | Allocazione iniziale (neutral / custom) | `execute_eom_backtest()` |

---

## Warmup Period

Nel file `data_preparation/base.py`:

```python
def prepare_market_df(db: Session, run, warmup_days: int = 260):
    """Carica dati con 260 giorni di warmup (52 settimane per IV Rank)."""
```

**Aumentato da 40 a 260 giorni** per supportare IV Rank a 252 giorni.

---

## Esempio: Creare un BacktestRunParameter

```python
from app.backtest.schemas.backtest_run_parameter import BacktestRunParameter

param = BacktestRunParameter(
    run_id=123,
    key="iv_rank.lookback_days",
    value="252",
    unit="days"
)
db.add(param)
db.commit()
```

Oppure via API REST (endpoint da creare):
```
POST /backtest/{run_id}/parameters
{
  "key": "iv_rank.lookback_days",
  "value": "252",
  "unit": "days"
}
```
