# Backtest

## Struttura dati

Il backtest è organizzato su due livelli:

- **Backtest** (container): definisce la strategia con `frequency` e `primary_index`
- **BacktestRun** (esecuzione): eredita frequency e primary_index dal container, aggiunge il periodo (start/end) e accumula le metriche

### Frequenze supportate
| Valore | Descrizione |
|--------|-------------|
| `EOM`  | End of Month — iterazione mensile guidata dall'indice primario |
| `EOW`  | End of Week |
| `EOD`  | End of Day |

### Indice primario
L'indice primario determina il ritmo di ribilanciamento. Attualmente:
- `MacroScore` — ribilancia quando aggiornato il MacroPillar (date MS, convenzione FRED)

## Logica EOM + MacroScore

Per ogni coppia di date consecutive dell'indice primario `(d_i, d_{i+1})`:

1. **Decisione** a `d_i` (MS, es. 2024-01-01): legge MacroScore → calcola pesi `W_i`
2. **Trade** se `W_i ≠ W_{i-1}`
3. **Ritorno applicato**: `prezzo(EOM d_{i+1}) / prezzo(EOM d_i) − 1`

**No look-ahead**: la decisione a `d_i` usa solo dati ≤ `d_i`. I prezzi EOM sono usati come outcome futuro, mai come input alla decisione.

## Allocation engine

La matrice di allocazione è interamente su DB (`sensitivity_coefficients`, `asset_classes`, `allocation_parameters`).
Viene **snapshotted** al momento dell'esecuzione nel campo `config_snapshot` del run (JSON), così i run storici mantengono la matrice originale anche se la configurazione cambia.

Contenuto dello snapshot:
```json
{
  "sensitivity": { "Growth": { "Equity": 1.0, ... }, ... },
  "neutral": { "Equity": 0.50, "Bond": 0.30, "Commodities": 0.10, "Cash": 0.10 },
  "scale_k": 0.05,
  "max_abs_delta": 0.10,
  "macro_score_weights": { "Growth": 0.3, "Inflation": -0.3, ... }
}
```

## Delta engine (allocation/engine.py)

Per ogni pillar `p` con score `s`:
1. **Saturazione**: `f(s) = clamp(s/2, -1, 1)` (satura a ±1 oltre ±2σ)
2. **Raw tilt**: `raw[asset] += f(s) × sensitivity[p][asset]`
3. **Scala**: `raw[asset] *= K` (default K=5%)
4. **Centra**: `delta[asset] = raw[asset] − mean(raw)` → somma delta = 0
5. **Cap**: `|delta[asset]| ≤ MAX_ABS` (default ±10%)
6. **Peso finale**: `neutral[asset] + delta[asset]`

Il vincolo zero-sum spiega i delta opposti osservati (Equity/Cash e Bond/Commodities hanno coefficienti speculari su Growth e Risk).

## Metriche calcolate per run

| Metrica | Descrizione |
|---------|-------------|
| CAGR | Rendimento annuo composto |
| Volatility | Deviazione standard annualizzata dei ritorni mensili |
| Sharpe Ratio | CAGR / Volatility |
| Max Drawdown | Massima perdita picco-valle sul NAV |
| Win Rate | % di periodi con ritorno positivo |
| Profit Factor | Somma guadagni / |somma perdite| |
| N. Trades | Cicli in cui l'allocazione è variata |

Le metriche vengono ricalcolate e committate **ad ogni ciclo** durante l'esecuzione.

## Portafoglio neutro (riferimento)

| Asset | Proxy | Neutro | Max |
|-------|-------|--------|-----|
| Equity | SPY | 50% | 70% |
| Bond | IEF | 30% | 55% |
| Commodities | DBC | 10% | 30% |
| Cash | BIL | 10% | 30% |

## Tabelle DB

| Tabella | Contenuto |
|---------|-----------|
| `backtests` | Container: name, frequency, primary_index, strategy_version |
| `backtest_runs` | Esecuzione: period, status, metrics, config_snapshot |
| `backtest_weights` | Allocazione per data e asset class (con macro_score, pillar_scores) |
| `backtest_performance` | NAV e ritorno mensile per ogni ciclo |

## Re-esecuzione

Un run può essere ri-eseguito: i dati precedenti (weights, performance) vengono cancellati e le metriche azzerata prima di ripartire. Lo stato torna a `RUNNING`.

## Stop

Durante l'esecuzione è possibile inviare un segnale di stop (`stop_requested = True`). Il background thread controlla il flag ad ogni ciclo e termina con stato `STOPPED`, salvando le metriche parziali.
