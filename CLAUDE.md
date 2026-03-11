# CLAUDE.md — Investment System

## Cos'è questo progetto
Sistema di investimento a tre layer con logica top-down:
- **Short** (trading) → genera profitti operativi, eccedenza alimenta Medium
- **Medium** (reddito) → garantisce flusso costante, eccedenza alimenta Long
- **Long** (macro) → accumulo e riallocazione strategica del capitale

Flusso di capitale: Short → Medium → Long (bottom-up)
Ogni layer ha il proprio orizzonte temporale, strumenti e logica decisionale.
Il codice esiste già — questo file serve a non perdere contesto tra sessioni.

## Stack tecnico
<!-- Aggiorna con il tuo stack reale -->
- Linguaggio principale: Python
- Dati di mercato: yfinance, IBKR API, FRED
- Backtest engine: Backtrader, VectorBT, custom
- Storage: PostgreSQL
- Frontend: Webapp React, Mobile (React-native Expo)

## Struttura del repo
```
investment/
├── CLAUDE.md
├── docs/
│   ├── idea.md             # visione e obiettivi
│   ├── architecture.md     # architettura dei tre layer
│   ├── requirements.md     # requisiti per layer
│   └── decisions/          # ADR — perché abbiamo scelto X invece di Y
├── layers/
│   ├── long/               # logica macro
│   ├── medium/             # logica reddito
│   └── short/              # logica trading
├── data/                   # fetch, pulizia, normalizzazione dati
├── backtest/               # risultati e script di backtest
└── tests/
```

## Convenzioni di codice
<!-- Aggiorna con le tue preferenze -->
- Nomi funzioni: snake_case
- Ogni modulo ha il suo README con input/output attesi
- I backtest salvano sempre i risultati in `backtest/results/` con timestamp

## Comandi utili
```bash
# Aggiorna dati di mercato
# python data/fetch.py --layer short

# Esegui backtest layer short
# python backtest/run.py --layer short --period 2022-2024

# Avvia dashboard
# streamlit run app.py
```

## Stato attuale
- [x] Layer short: backtest su ETF completato
- [x] Layer short: studio opzioni call/put avviato
- [ ] Layer short: backtest su futures in corso
- [ ] Layer medium: logica da definire
- [ ] Layer long: indicatori macro individuati, logica da formalizzare
- [ ] Integrazione tra layer

## Sessione precedente — note rapide
<!-- Aggiorna ad ogni sessione con cosa hai fatto e dove ti sei fermato -->
_ultima sessione: struttura del progetto e documentazione iniziale_
