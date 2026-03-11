# Requirements — Investment System

## Layer Short

### Funzionali
- [ ] Fetch dati OHLCV per ETF e sottostanti opzioni
- [ ] Calcolo indicatori tecnici con denoising del segnale
- [ ] Generazione segnali entrata/uscita con livello di confidenza
- [ ] Calcolo sizing della posizione (% capitale, risk per trade)
- [ ] Esecuzione backtest su serie storica con metriche standard
- [ ] Log di ogni operazione (entry, exit, P&L, motivazione del segnale)

### Backtest — metriche minime richieste
- Sharpe Ratio
- Max Drawdown
- Win Rate
- Profit Factor
- Numero di trade (statistica significativa: min 30)

### Strumenti supportati
- [x] ETF long/short
- [x] Opzioni call e put (backtest fatto)
- [ ] Futures (in studio)

### Non funzionali
- Latenza fetch dati: < 5 secondi per aggiornamento daily
- Backtest su 3+ anni di dati prima di andare live
- Ogni strategia documentata in `backtest/` con data e parametri usati

---

## Layer Medium

### Funzionali (da completare)
- [ ] Definire strategia income principale
- [ ] Calcolo reddito mensile atteso
- [ ] Logica di redistribuzione eccedenza verso Long
- [ ] Alert se reddito target non raggiunto

### Note
Layer meno definito — priorità dopo Short stabilizzato.
Candidati strategia: covered call su posizioni Long, bond ladder, ETF dividendi.

---

## Layer Long

### Funzionali
- [ ] Fetch indicatori macro (da lista da definire)
- [ ] Scoring macro per asset class
- [ ] Calcolo allocation target con pesi
- [ ] Trigger ribilanciamento su deviazione soglia
- [ ] Report mensile stato portafoglio vs target

### Indicatori macro (lista provvisoria — da validare)
- Yield curve (spread 2y-10y)
- CPI / inflazione
- PMI manifatturiero e servizi
- Disoccupazione
- [ ] altri da aggiungere

### Non funzionali
- Aggiornamento settimanale automatico
- Storico indicatori conservato per analisi retrospettiva

---

## Sistema generale

### Non funzionali
- Tutto il codice testabile in locale senza connessione live ai mercati (mock data)
- Configurazione via file (non hardcoded): soglie, parametri, target
- Dashboard leggibile anche da mobile
- Nessuna dipendenza da piattaforme proprietarie non esportabili
