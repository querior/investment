# Idea — Investment System

## Problema
Gestire capitale su orizzonti temporali diversi richiede logiche e strumenti differenti.
La maggior parte degli approcci tratta ogni orizzonte in modo isolato, perdendo le sinergie
tra flussi di capitale e segnali macro.

## Soluzione
Un sistema a tre layer interconnessi dove ogni layer ha una responsabilità precisa
e alimenta il successivo in modo strutturato (bottom-up).

## I tre layer

### Short (trading)
- **Orizzonte**: daily → pochi mesi
- **Logica**: vantaggio statistico su movimenti di mercato depurati dal rumore
- **Strumenti**: ETF, opzioni (call/put), futures (in studio)
- **Input**: segnali tecnici filtrati, livelli di volatilità
- **Output**: operazioni con edge statistico documentato + eccedenza verso Medium

### Medium (reddito)
- **Orizzonte**: mesi
- **Logica**: garantire un flusso di reddito costante e prevedibile
- **Strumenti**: da definire (dividendi? obbligazioni? covered call?)
- **Input**: eccedenza da Short, obiettivo di reddito mensile
- **Output**: reddito periodico + eccedenza reinvestita in Long
- **Nota**: layer meno definito, da approfondire

### Long (macro)
- **Orizzonte**: anni
- **Logica**: riallocazione del capitale sulla base di segnali macroeconomici
- **Strumenti**: ETF settoriali, asset class, commodity, bond
- **Input**: indicatori macro (yield curve, CPI, PMI, ecc.)
- **Output**: allocazione target del portafoglio, ribilanciamenti periodici

## Flusso di capitale
```
Short ──(eccedenza)──► Medium ──(eccedenza)──► Long
  │                       │
(operatività)        (reddito costante)
```

Il flusso è bottom-up: Short genera liquidità operativa, l'eccedenza scala verso
Medium che la consolida in reddito, l'eccedenza di Medium accumula nel Long.

## Esecuzione semi-automatica (roadmap)

Quando il sistema sarà maturo, il layer Short potrà operare in modalità semi-automatica
tramite un agente di esecuzione parametrico.

### Strategia come configurazione
Ogni strategia viene definita come un insieme di parametri espliciti:
- Segnali di entrata e uscita
- Allocazione capitale per singolo trade
- Rischio massimo per operazione (es. % del capitale, stop loss)
- Strumento target (ETF, opzione call/put, future)
- Orizzonte temporale atteso del trade
- Altri parametri da definire

### Modalità di esecuzione dell'agente
L'agente può operare in due modalità configurabili:

**Automatica** — esegue autonomamente apertura/chiusura posizioni tramite API del broker,
entro i parametri definiti dalla strategia.

**Human-in-the-loop** — suggerisce il trade con motivazione, attende conferma prima
di eseguire. Utile nelle fasi iniziali o per strumenti complessi come i derivati.

### Prerequisiti prima dell'automazione
- [ ] Backtest validato su almeno 3 anni di dati
- [ ] Strategia documentata con metriche (Sharpe, drawdown, win rate)
- [ ] Parametri di rischio definiti e testati
- [ ] Integrazione API broker implementata e testata in paper trading
- [ ] Monitoring e alerting attivi

## Obiettivo finale
Non battere il mercato in modo speculativo, ma costruire un vantaggio statistico
documentato su ogni layer con rischio controllato e sizing appropriato.
L'automazione è uno strumento, non il fine — ogni strategia automatizzata deve
essere prima compresa e validata manualmente.

## Fuori scope (per ora)
- Criptovalute
- Forex
- Leva elevata
- HFT / strategie ad alta frequenza

## Evoluzione futura — Trading semi-automatico

Quando il sistema sarà maturo, il layer Short potrà operare in modalità semi-automatica
o automatica tramite un agente parametrico.

### Modalità operative
- **Manuale**: segnali generati dal sistema, esecuzione interamente a carico dell'utente
- **Semi-automatica**: l'agente suggerisce il trade o chiede conferma prima di eseguire
- **Automatica**: l'agente esegue autonomamente entro i parametri definiti dalla strategia

### Strategia come configurazione
Ogni strategia è un oggetto parametrico che definisce:
- Strumento (ETF, opzione call/put, future, ecc.)
- Segnali di entrata e uscita
- Allocazione capitale per singolo trade
- Soglia di rischio massimo (per trade e complessivo)
- Stop loss / take profit
- Modalità operativa (manuale / semi-auto / auto)
- Altri parametri da definire

### Agente di esecuzione
L'agente ha un set di azioni limitate e ben definite:
- Apre una posizione tramite API del broker
- Chiude una posizione tramite API del broker
- Notifica e chiede conferma all'utente (modalità semi-auto)
- Logga ogni operazione con motivazione e parametri usati

### Principio di sicurezza
L'automazione opera **sempre dentro i vincoli della strategia configurata**.
Nessuna azione fuori parametro è consentita senza intervento esplicito dell'utente.
I parametri di rischio sono il primo guardrail, non l'ultimo.

### Fuori scope per ora
- Definizione dell'API broker specifica
- Architettura dettagliata dell'agente
- Gestione errori e fallback operativi