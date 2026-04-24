# 📘 Backtest UI v2 — Specifica

---

## 1. Obiettivo

Rendere la UI del detail di un backtest run **leggibile e analitica**, non solo descrittiva:

- parametri con contesto esplicativo (perché esiste quel parametro)
- posizioni con criteri di entrata e uscita chiari
- analisi del funnel di entry (perché non si entra)
- grafico principale che mostra dove si è entrati e usciti sul prezzo reale

---

## 2. Principio guida

```
ogni elemento visibile deve rispondere a una domanda specifica
parametri → "cosa sto controllando?"
posizione → "perché sono entrato? perché sono uscito?"
funnel     → "dove si perde il segnale?"
grafico    → "dove sul mercato è successo?"
```

---

## 3. Punto 1 — Parametri esplicativi

### Obiettivo

Capire cosa si sta modificando quando si variano i parametri, senza dover consultare documentazione esterna.

### Layout attuale

```
[ EXECUTION PARAMETERS ]
Tab: Entry | Strategy | Exit | Pipeline
  param_name: value
```

### Layout v2

```
[ EXECUTION PARAMETERS ]
Tab: Entry | Strategy | Exit | Pipeline
     └── riga descrittiva del tab

  Label leggibile
  param_name: value
  Descrizione breve del parametro
```

### Dati necessari

- `PARAMETER_LABELS` map: label leggibile per ogni parametro
- `PARAMETER_HINTS` map: già esistente, descrive ogni parametro (usato come tooltip)
- Descrizione per ogni tab:
  - **Entry** → "Filtri e scoring per selezionare quando entrare"
  - **Strategy** → "Allocazione del capitale e coerenza tra strategie"
  - **Exit** → "Regole di chiusura anticipata delle posizioni"
  - **Pipeline** → "Indicatori tecnici e calcolo dei regimi di mercato"

### Dati già disponibili

- `PARAMETER_HINTS` in `ParameterEditor.tsx` (tooltip già implementati)
- `PARAMETER_SCHEMA` a backend con `type`, `min`, `max`, `default`, `unit`

### Dati mancanti

- `PARAMETER_LABELS`: label leggibili — vanno aggiunti a frontend
- Descrizioni dei tab: hardcoded

---

## 4. Punto 2 — Criteri di entrata e uscita per posizione

### Obiettivo

Per ogni posizione aperta o chiusa, vedere immediatamente:
- lo stato del mercato al momento dell'entrata
- quale regola ha causato la chiusura

### Layout attuale (expanded row)

```
[ header: status, date, P&L ]
[ entry_criteria list ]  [ exit_criteria list ]
[ daily history table ]
[ price chart ]  [ performance chart ]
```

### Layout v2

```
[ header: status, date, P&L, realized_pnl ]

[ ENTRATA ]                        [ USCITA ]
IV al entry: 0.28                  Regola: DTE_EXIT
RSI al entry: 52                   Motivazione: "DTE < 21, chiuso a scadenza"
Macro regime: RISK_ON              IV al close: 0.31
Macro score: 72                    RSI al close: 48
Trend: UP                          Macro al close: RISK_ON
EV netto: +$42                     Delta al close: -0.18
Prob profit: 68%                   DTE residuo: 18

[ daily history table ]
[ price chart ]  [ performance chart ]
```

### Dati necessari

| Campo | Fonte | Disponibile |
|-------|-------|-------------|
| `entry_conditions.iv` | `BacktestPosition.entry_conditions` JSON | In DB, non esposto da API |
| `entry_conditions.rsi_14` | idem | In DB, non esposto da API |
| `entry_conditions.macro_regime` | idem | In DB, non esposto da API |
| `entry_conditions.macro_score` | idem | In DB, non esposto da API |
| `entry_conditions.trend` | idem | In DB, non esposto da API |
| `entry_ev_net` | `BacktestPosition.entry_ev_net` | In DB, non esposto da API |
| `entry_prob_profit` | `BacktestPosition.entry_prob_profit` | In DB, non esposto da API |
| `exit_conditions.triggered_by` | `BacktestPosition.exit_conditions` JSON | In DB, non esposto da API |
| `exit_conditions.reason` | idem | In DB, non esposto da API |
| `exit_conditions.data.*` | idem | In DB, non esposto da API |

### Dati mancanti

Nessun dato mancante a livello di DB — tutti i campi esistono in `BacktestPosition`.
Serve solo esporre `entry_conditions`, `exit_conditions`, `entry_ev_net`, `entry_prob_profit`
nell'endpoint `GET /backtests/{id}/runs/{run_id}/positions`.

---

## 5. Punto 3 — Tabella analisi del funnel di entry

### Obiettivo

Capire perché la maggior parte degli entry checks non si converte in trade aperto.

### Layout

```
┌────────────────────┬───────┬──────┬───────────────────────────────────┐
│     Categoria      │ Count │  %   │               Note                │
├────────────────────┼───────┼──────┼───────────────────────────────────┤
│ ENTRY CHECKS       │  115  │ 100% │ Ogni N giorni (entry_every_n_days)│
├────────────────────┼───────┼──────┼───────────────────────────────────┤
│ OCCUPIED           │   5   │  4%  │ Portfolio già pieno               │
├────────────────────┼───────┼──────┼───────────────────────────────────┤
│ COOLDOWN           │   3   │  3%  │ Stessa strategia già chiusa di    │
│                    │       │      │ recente (cooldown_days)           │
├────────────────────┼───────┼──────┼───────────────────────────────────┤
│ NO_TRADE           │  55   │  48% │ Strategy selector non trova setup │
├────────────────────┼───────┼──────┼───────────────────────────────────┤
│ IV_FILTER          │  18   │  16% │ IV < iv_min_threshold             │
├────────────────────┼───────┼──────┼───────────────────────────────────┤
│ SIZE_ZERO          │  27   │  23% │ Entry score < soglia minima       │
├────────────────────┼───────┼──────┼───────────────────────────────────┤
│ DEBIT_SKIP         │   5   │  4%  │ Premium negativo (trade a debito) │
├────────────────────┼───────┼──────┼───────────────────────────────────┤
│ ACCEPTED           │   8   │  7%  │ ✅ Trade effettivamente aperti    │
└────────────────────┴───────┴──────┴───────────────────────────────────┘
```

### Dati necessari

| Campo | Fonte | Disponibile |
|-------|-------|-------------|
| `total_checks` | calcolato da `entry_every_n_days` + durata run | Derivabile |
| `outcome` per ogni check | log temporaneo durante esecuzione | **Non in DB** |
| `entry_score` al momento del check | calcolato e scartato | **Non in DB** |
| `iv` al momento del check | calcolato e scartato | **Non in DB** |

### Dati mancanti

Tutti i rejected attempts non vengono persistiti. Esistono solo come log durante l'esecuzione.

### Opzioni di implementazione

**Opzione A — Persistenza completa (alta fedeltà)**
- Nuova tabella `BacktestEntryAttempt` con: date, outcome, strategy_name, entry_score, size_multiplier, iv
- Modifica al backtest engine per salvare ogni tentativo
- Nuovo endpoint `GET .../entry-analysis`
- ⚠️ Richiede DB migration + re-run di tutti i backtest esistenti

**Opzione B — Stima approssimata (senza re-run)**
- `total_checks` = durata run in giorni / `entry_every_n_days`
- `ACCEPTED` = numero posizioni in DB
- Gli altri bucket non sono distinguibili senza dati storici
- Precisione bassa, utile solo come indicatore grossolano

---

## 6. Punto 4 — Grafico prezzo sottostante con markers entry/exit

### Obiettivo

Visualizzare **dove sul mercato** si è entrati e usciti da ogni posizione, nel contesto del prezzo del sottostante per tutta la durata del backtest.

### Layout

```
[ Underlying Price — intero periodo backtest ]

linea grigia: prezzo SPY (o sottostante configurato)

▲ verde: entry di ogni posizione
▼ rosso: exit di ogni posizione
colore: legato alla strategia (strategy_color)

Tooltip su hover:
  - data
  - strategia
  - P&L realizzato
  - motivazione exit (se chiusa)
```

### Dati necessari

| Campo | Fonte | Disponibile |
|-------|-------|-------------|
| Serie giornaliera `underlying_price` | `BacktestPortfolioPerformance.underlying_price` | In DB, non in response `/nav` |
| `opened_at` + `entry_underlying` per ogni posizione | `BacktestPosition` | Già esposto da API |
| `closed_at` + `strategy_color` per ogni posizione | `BacktestPosition` | Già esposto da API |
| `realized_pnl` per tooltip | `BacktestPosition` | Già esposto da API |

### Dati mancanti

`underlying_price` non è incluso nella response dell'endpoint `/nav`.
Va aggiunto al payload: `{ date, nav, period_return, underlying_price }`.

---

## 7. Riepilogo impatto

| Punto | DB migration | Re-run backtest | Backend | Frontend | Complessità |
|-------|-------------|-----------------|---------|----------|-------------|
| 1 - Parametri esplicativi | No | No | No | Sì | Bassa |
| 2 - Entry/Exit criteria | No | No | Sì (leggero) | Sì | Media |
| 4 - Grafico prezzo+markers | No | No | Sì (leggero) | Sì | Media |
| 3 - Tabella analisi funnel | **Sì** (opzione A) | **Sì** | Sì (medio) | Sì | Alta |

---

## 8. Domande aperte

1. **Punto 3 — Opzione A o B?** Vogliamo la fedeltà completa del funnel (richiede re-run) o una stima approssimativa subito?
2. **Punto 4 — grafico principale o aggiuntivo?** Il grafico NAV attuale resta, o viene sostituito dal grafico prezzo+markers?
3. **Punto 1 — lingua delle label?** Italiano o inglese?

---

## 9. Stato

Spec v2 — definizione funzionale completa

⚠️ Nessuna implementazione tecnica in questa fase
