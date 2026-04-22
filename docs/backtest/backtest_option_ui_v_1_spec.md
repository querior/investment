# 📘 Backtest UI v1 — Specifica

---

## 1. Obiettivo

Costruire una UI per l’analisi di strategie opzionali che:

- separi chiaramente **evoluzione temporale** e **struttura della strategia**
- supporti analisi di:
  - entry
  - monitoring
  - exit
- permetta lettura immediata di rischio e rendimento

---

## 2. Principio guida

```
sinistra = path (storia)
destra = shape (struttura)
```

---

## 3. Layout generale

```
[ header posizione ]

LEFT (tempo)              RIGHT (prezzo)

Underlying                Payoff
PnL                       Value curve
IV                        Greeks (optional)
```

---

## 4. Header posizione

Contiene:

- strategy_type
- status (OPEN / CLOSED)
- opened_at / closed_at
- entry_underlying
- entry_iv
- macro_regime
- realized_pnl
- days_in_trade

---

## 5. Colonna sinistra — Time based

### 5.1 Underlying vs Time

Contenuti:
- linea prezzo
- marker:
  - entry
  - exit
  - eventi
- linee opzionali:
  - strike
- zone:
  - profit / risk

Scopo:
- capire contesto mercato

---

### 5.2 PnL vs Time

Contenuti:
- pnl cumulato
- evidenza:
  - drawdown
  - profit zone

Scopo:
- valutare performance reale

---

### 5.3 IV vs Time

Contenuti:
- serie IV
- spike evidenziati

Scopo:
- spiegare movimenti non dovuti al prezzo

---

## 6. Colonna destra — Price based

### 6.1 Payoff vs Price

Contenuti:
- curva payoff a scadenza
- marker:
  - spot corrente
- linee:
  - short strike
  - long strike
- zone:
  - profit
  - loss

Scopo:
- capire struttura finale

---

### 6.2 Value (Now) vs Price

Contenuti:
- curva valore posizione oggi
- marker:
  - spot corrente

Scopo:
- capire rischio attuale e non solo finale

---

### 6.3 Greeks vs Price (optional)

Contenuti:
- delta
- gamma
- theta
- vega

Scopo:
- analisi avanzata sensibilità

---

## 7. Interazioni

### 7.1 Crosshair sincronizzato (tempo)

- linea verticale condivisa tra grafici time-based
- mostra:
  - date
  - underlying
  - pnl
  - iv

---

### 7.2 Sincronizzazione tempo ↔ prezzo

- selezione di un punto nei grafici time-based (sinistra):
  - evidenzia il corrispondente **spot price** nei grafici price-based (destra)
  - disegna una linea verticale su payoff e value curve

- selezione di un punto nei grafici price-based (destra):
  - evidenzia il punto temporale più vicino nei grafici time-based (sinistra)
  - aggiorna crosshair su tutti i grafici

Scopo:
- collegare **quando** (tempo) con **dove** (prezzo)

---

### 7.3 Tooltip condiviso

Contenuti:
- date
- underlying_price
- position_pnl
- iv
- strategy_type

---

### 7.4 Zoom / Brush

- selezione range temporale
- sincronizzata tra grafici

---

### 7.5 Toggle visualizzazioni

- mostra strike
- mostra zone
- mostra greche

---

### 7.2 Tooltip condiviso

Contenuti:
- date
- underlying_price
- position_pnl
- iv
- strategy_type

---

### 7.3 Zoom / Brush

- selezione range temporale
- sincronizzata tra grafici

---

### 7.4 Toggle visualizzazioni

- mostra strike
- mostra zone
- mostra greche

---

## 8. Insight supportati

### 8.1 Entry

- posizione dello spot rispetto agli strike
- shape payoff
- spazio di sicurezza

---

### 8.2 Monitoring

- evoluzione pnl
- impatto IV
- stabilità strategia

---

### 8.3 Exit

- distanza da zona critica
- profitto residuo
- asimmetria rischio

---

## 9. Requisiti dati (alto livello)

### Time series

- date
- underlying_price
- position_pnl
- iv

### Strategy

- legs
- strikes
- expiry
- strategy_type

### Events

- entry
- exit
- regime change

---

## 10. Obiettivo finale

```
trasformare i grafici da descrittivi a decisionali
```

La UI deve permettere di rispondere a:

1. cosa è successo?
2. perché è successo?
3. dove sono ora?
4. cosa può succedere?
5. conviene entrare o uscire?

---

## 11. Stato

Spec v1 — definizione funzionale completa

⚠️ Nessuna implementazione tecnica in questa fase

