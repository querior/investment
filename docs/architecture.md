# Architecture — Investment System

## Principio architetturale
Ogni layer è **indipendente** nella sua logica interna ma **connesso** tramite
un bus di capitale e segnali condivisi. Nessun layer conosce i dettagli interni degli altri.

## Schema generale

```
┌─────────────────────────────────────────────┐
│                  DATA LAYER                  │
│  fetch → normalize → store → serve          │
└──────────────────┬──────────────────────────┘
                   │
       ┌───────────┼───────────┐
       ▼           ▼           ▼
  ┌─────────┐ ┌─────────┐ ┌─────────┐
  │  SHORT  │ │ MEDIUM  │ │  LONG   │
  │  layer  │ │  layer  │ │  layer  │
  └────┬────┘ └────┬────┘ └─────────┘
       │           │           ▲
       └──────────►┘           │
                   └───────────┘
              (flusso bottom-up)
                   │
                   ▼
          ┌─────────────────┐
          │   DASHBOARD /   │
          │   REPORTING     │
          └─────────────────┘
```

## Mapping layer → codice

```
backend/app/
├── services/
│   ├── config_repo.py  ← lettura configurazione da DB (unico punto)
│   ├── allocation/     ← Layer Long (esistente)
│   ├── pillars/        ← Layer Long (esistente)
│   ├── ingest/         ← Data Layer (esistente)
│   ├── transforms/     ← Data Layer (esistente)
│   ├── processed/      ← Data Layer (esistente)
│   ├── medium/         ← Layer Medium (da creare)
│   ├── short/          ← Layer Short (da creare)
│   └── user_service.py
├── jobs/
│   ├── macro_pipeline.py   ← orchestrazione Long
│   ├── market_pipeline.py  ← orchestrazione Data Layer
│   └── scheduler.py
├── scripts/
│   └── seed_config.py  ← popola le tabelle di configurazione
└── backtest/               ← trasversale a tutti i layer
    ├── schemas/            ← Backtest, BacktestRun, BacktestWeight, BacktestPerformance
    ├── runs.py             ← execute_backtest, run_in_background
    ├── loaders.py          ← load_asset_returns (con resample EOM/EOW/EOD)
    ├── metrics.py          ← compute_metrics (CAGR, Sharpe, Vol, MaxDD, WinRate, PF)
    └── init_db.py          ← creazione tabelle + migrazione incrementale
```

## Config Layer

La configurazione del sistema (indicatori, pillar, score, allocation) è interamente
su database e non più hardcoded. Il flusso di accesso è:

```
DB (tabelle config)
     │
     ▼
services/config_repo.py   ← unico punto di lettura
     │
     ├── services/processed/orchestrator.py
     ├── services/pillars/service.py
     ├── services/allocation/engine.py
     ├── services/ingest/market.py
     └── api/ (data, ingest, allocation)
```

### Tabelle di configurazione

| Tabella | Contenuto |
|---|---|
| `indicators` | Ticker FRED con source, frequency, description |
| `market_symbols` | Simboli Yahoo/IBKR con asset_type |
| `processed_indicators` | Trasformazioni raw→processed (yoy/level/delta, window, clip) |
| `pillars` | Definizione dei 4 pillar |
| `pillar_components` | Mapping pillar → processed indicator |
| `composite_scores` | Definizione degli score compositi (es. MacroScore) |
| `composite_score_weights` | Pesi pillar per ogni score |
| `regime_thresholds` | Soglie di regime per ogni score |
| `asset_classes` | Asset class con neutral_weight, max_weight, proxy symbol |
| `sensitivity_coefficients` | Matrice di sensibilità pillar × asset |
| `allocation_parameters` | Parametri scalari engine (K, MAX_ABS) |

Per popolare le tabelle: `python -m app.scripts.seed_config`

## Data Layer
Responsabilità: unica fonte di verità per i dati di mercato.
Moduli: `services/ingest/`, `services/transforms/`, `services/processed/`

- **Fetch**: recupera dati da sorgenti esterne (API, file)
- **Normalize**: formato standard per tutti i layer
- **Store**: persistenza locale (evita chiamate API ripetute)
- **Serve**: interfaccia uniforme che i layer usano per richiedere dati

Ogni layer non chiama direttamente le API esterne — passa sempre dal Data Layer.

## Layer Long
Moduli: `services/allocation/`, `services/pillars/`
- Frequenza di aggiornamento: settimanale / mensile
- Input: indicatori macro (CPI, yield curve, PMI, ecc.)
- Output: `allocation_target` con pesi per asset class
- Trigger ribilanciamento: soglia di deviazione dall'allocation target

## Layer Medium
Moduli: `services/medium/` (da creare)
- Frequenza di aggiornamento: mensile
- Input: eccedenza da Short, obiettivo reddito, capitale disponibile
- Output: posizioni income + quota da redirigere a Long
- **Da definire**: strategia specifica (covered call, bond ladder, dividendi?)

## Layer Short
Moduli: `services/short/` (da creare), `backtest/`
- Frequenza di aggiornamento: daily / intraday
- Input: dati OHLCV, indicatori tecnici filtrati, volatilità implicita
- Output: segnali di entrata/uscita con sizing calcolato
- Backtest: ogni strategia deve avere un backtest documentato prima del live

## Capital Bus
Gestisce i trasferimenti tra layer (flusso bottom-up):
- Short → Medium: eccedenza rispetto al buffer operativo di Short
- Medium → Long: eccedenza dopo che il reddito target è soddisfatto

Il Long è il layer terminale — accumula ma non redistribuisce verso il basso.
Non è previsto flusso inverso in condizioni normali.

## Decisioni architetturali aperte
- [ ] Come gestire la sincronizzazione dei layer (event-driven vs scheduled?)
- [ ] Soglie di trasferimento capital bus: fisse o dinamiche?
- [ ] Layer Medium: strategia income da definire

## Decisioni prese
Vedi `docs/decisions/` per i dettagli.