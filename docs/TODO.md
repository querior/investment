# TODO

## Layer Long
- [ ] Ricalcolare serie `_M` dopo fix `resample("MS")` (eliminare record esistenti e rieseguire MacroScore)
- [ ] Calibrazione matrice di sensibilità sui dati storici
- [ ] Test di reazione agli shock (2008, 2020, 2022)
- [ ] Verifica comportamento nei quattro regimi (Espansione, Ripresa, Rallentamento, Recessione)
- [ ] Paper trading su almeno un ciclo mensile completo

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
