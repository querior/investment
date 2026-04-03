# TODO

## Layer Long
- [x] Pipeline di calcolo allineata alla spec (smoothing → z-score → EMA per indicatore → pillar score)
- [x] Rimossa EMA a livello pillar (ora per indicatore in `process_indicator`)
- [x] `macro_processed`: aggiunta `z_score_ema`, rimossa `z_score_percentile`
- [x] Eliminato MacroScore (indice sintetico) — logica ora regime-based per pillar
- [x] Rimossi: sensitivity_coefficients, pillar_signal_parameters, composite_scores, regime_thresholds
- [x] Backtest migrato da MacroPillar+sensitivity engine a MacroRegime+compute_target_allocation
- [ ] Eseguire migrazione DB (`migrate_macro_processed_ema.py`) e ricalcolare pipeline
- [ ] Calibrazione matrice di sensibilità sui dati storici
- [ ] Test di reazione agli shock (2008, 2020, 2022)
- [ ] Verifica comportamento nei quattro regimi (Espansione, Ripresa, Rallentamento, Recessione)
- [ ] Paper trading su almeno un ciclo mensile completo

## Backtest
- [x] Struttura Backtest (container) → BacktestRun (esecuzione)
- [x] Frequenza EOM con resample mensile dei prezzi
- [x] No look-ahead: MacroPillar.date ≤ d, ritorno su periodo futuro
- [x] Config snapshot per storicizzare la matrice usata in ogni run
- [x] Metriche in real-time (CAGR, Sharpe, Vol, MaxDD, WinRate, PF, N.Trades)
- [x] Grafico NAV aggiornato ad ogni ciclo di polling
- [x] Stop/restart idempotente del run
- [ ] Rendere editabile la matrice di allocazione al fine di gestire differenti tipi di allocazione
- [ ] Supporto frequenze EOW e EOD nel loader
- [ ] Benchmark di confronto (es. SPY buy&hold) nel grafico NAV
- [ ] Export CSV dei risultati

## Backend — API
- [ ] CRUD per gestione dinamica di indicatori (`macro_indicators`)
- [ ] CRUD per gestione dinamica di market symbols (`market_symbols`)
- [ ] CRUD per gestione dinamica di processed indicators (`processed_indicators`)
- [ ] CRUD per gestione dinamica di pillar e pillar components
- [ ] CRUD per gestione dinamica di composite scores, pesi e regime thresholds

## Layer Medium
- [ ] Logica da definire

## Layer Short
- [ ] Backtest su futures in corso

## Integrazione
- [ ] Integrazione tra layer

## Frontend 
[] Spostare EditableRunName e EditableDateRange di BacktestDetail in components
