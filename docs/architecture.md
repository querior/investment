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
└── backtest/               ← trasversale a tutti i layer
```

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