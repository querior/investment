# Layer Long — Documentazione

## Responsabilità
Analisi macroeconomica continua e riallocazione strategica del capitale
sulla base del regime di mercato corrente. Opera con cadenza mensile.

## Stato attuale
Sviluppo avanzato. Componenti implementate:
- [x] Selezione e configurazione indicatori (su database)
- [x] Ingestion dei dati (FRED + Yahoo Finance)
- [x] Resample a frequenza mensile per serie DAILY/WEEKLY
- [x] Normalizzazione (z-score con clipping ±2)
- [x] Smoothing pre z-score e EMA post z-score
- [x] Calcolo dei pillar score con inversione semantica
- [x] Regime detection per pillar (isteresi + conferma + segnali estremi)
- [ ] Backtest engine con metriche e UI
- [ ] Matrice di aggiustamento regime-based
- [ ] Smoothing allocazione mensile
- [ ] Calibrazione empirica portafogli per regime
- [ ] Validazione: reazione agli shock (2008, 2020, 2022)
- [ ] Paper trading / go live

Gestione: **manuale** — il sistema calcola e propone, l'utente approva.

---

## Pipeline

```
Indicatori raw (FRED / Yahoo Finance)
     │
     ▼
  Ingestion                    (services/ingest/)
     │
     ▼
  Resample mensile             resample("MS").mean()  ← solo per serie DAILY/WEEKLY
     │
     ▼
  Trasformazione               yoy | level | delta
     │
     ▼
  Smoothing pre z-score        rolling(smooth_window, min_periods=1).mean()
     │
     ▼
  Z-score + clipping           rolling(36).mean/std, clip ±2
     │
     ▼
  EMA sullo z-score            ewm(alpha=0.4, adjust=False)
     │
     ▼
  Pillar Score                 mean(z_ema) con inversione semantica
     │
     ▼
  Regime Detection             isteresi + conferma 2 mesi + segnali estremi
     │
     ▼
  Matrice di aggiustamento     delta per pillar × regime
     │
     ▼
  Allocazione target           base + Σ delta × coerenza
     │
     ▼
  Smoothing allocazione        EWM mensile verso target
     │
     ▼
  Portafoglio ribilanciato     (mensile, approvazione manuale)
```

---

## Indicatori e trasformazioni

Tutti i processed indicator hanno data di inizio mese (convenzione FRED).
Le serie non-mensili vengono resampled a `MS` (month start) con media prima
di qualsiasi trasformazione.

### Convenzione nomi
- Serie native mensili: nome invariato (es. `FEDFUNDS`, `CPI_YOY`)
- Serie resampled da DAILY/WEEKLY: suffisso `_M` (es. `VIXCLS_M`, `T10Y2Y_M`)

---

## I quattro Pillar

Ogni pillar produce uno score su scala z normalizzata. Gli indicatori con
segno invertito (valore alto = condizione negativa per il ciclo) vengono
moltiplicati per -1 al momento dell'aggregazione, non sulla serie grezza.

### Growth — forza del ciclo economico reale

| Processed indicator | Sorgente | Freq. raw | Trasformazione | Inversione |
|---|---|---|---|---|
| `CUMFNS` | CUMFNS | MONTHLY | level (diff 1) | No |
| `INDPRO_YOY` | INDPRO | MONTHLY | yoy % change | No |
| `W875RX1_YOY` | W875RX1 | MONTHLY | yoy % change | No |

```
GrowthScore = mean( z_ema(CUMFNS), z_ema(INDPRO_YOY), z_ema(W875RX1_YOY) )
```

### Inflation — pressione inflattiva realizzata e attesa

| Processed indicator | Sorgente | Freq. raw | Trasformazione | Inversione |
|---|---|---|---|---|
| `CPI_YOY` | CPIAUCSL | MONTHLY | yoy % change | Sì |
| `PPIACO_YOY` | PPIACO | MONTHLY | yoy % change | Sì |
| `EXPINF5YR` | EXPINF5YR | MONTHLY | level (diff 1) | Sì |

```
InflationScore = mean( -z_ema(CPI_YOY), -z_ema(PPIACO_YOY), -z_ema(EXPINF5YR) )
```

Nota: l'inversione fa sì che uno score alto indichi bassa pressione inflattiva,
coerente con la convenzione degli altri pillar.

### Policy — stance della banca centrale

| Processed indicator | Sorgente | Freq. raw | Trasformazione | Inversione |
|---|---|---|---|---|
| `FEDFUNDS` | FEDFUNDS | MONTHLY | level (diff 1) | Sì |
| `FEDFUNDS_DELTA` | FEDFUNDS | MONTHLY | delta (diff 1) | Sì |
| `T10Y2Y_M` | T10Y2Y | DAILY → resample MS | level (diff 1) | No |

```
PolicyScore = mean( -z_ema(FEDFUNDS), -z_ema(FEDFUNDS_DELTA), z_ema(T10Y2Y_M) )
```

Nota: rialzi del tasso e politica restrittiva producono score negativo.
La curva dei tassi (T10Y2Y) non viene invertita: una curva normale (positiva)
è associata a condizioni espansive.

### Risk — stress finanziario e risk aversion

| Processed indicator | Sorgente | Freq. raw | Trasformazione | Inversione |
|---|---|---|---|---|
| `BAA10Y_M` | BAA10Y | DAILY → resample MS | level (diff 1) | Sì |
| `VIXCLS_M` | VIXCLS | DAILY → resample MS | level (diff 1) | Sì |
| `NFCI_M` | NFCI | WEEKLY → resample MS | level (diff 1) | Sì |

```
RiskScore = mean( -z_ema(BAA10Y_M), -z_ema(VIXCLS_M), -z_ema(NFCI_M) )
```

Nota: spread elevati, VIX alto e condizioni finanziarie tese producono score negativo.

---

## Normalizzazione e Smoothing

### Parametri

| Parametro | Valore | Descrizione |
|---|---|---|
| `window` | 36 mesi | Finestra rolling per z-score |
| `smooth_window` | 3 mesi | Media mobile pre z-score sulla serie grezza |
| `ema_alpha` | 0.4 | Alpha EWM post z-score |
| `clip` | ±2 | Clipping dello z-score |

### Pipeline per indicatore

```python
# 1. smoothing pre z-score
value_smooth = value.rolling(smooth_window, min_periods=1).mean()

# 2. z-score + clip
z = (value_smooth - value_smooth.rolling(window).mean()) / value_smooth.rolling(window).std()
z = z.clip(-2, 2)

# 3. EMA
z_ema = z.ewm(alpha=0.4, adjust=False).mean()
```

La scelta di `window=36` copre un ciclo economico completo mantenendo
reattività ai cambi di regime. Finestre più corte (12-24) rendono lo z-score
instabile; finestre più lunghe (60+) rallentano eccessivamente la risposta.

---

## Regime Detection

Ogni pillar viene classificato indipendentemente in uno di tre regimi:
**expansion**, **neutral**, **contraction**.

### Soglie (in unità di z-score)

| Parametro | Valore |
|---|---|
| `THRESHOLD_UP` | +0.5 |
| `THRESHOLD_DOWN` | -0.5 |
| `HYSTERESIS` | 0.2 |
| `CONFIRM_MONTHS` | 2 |
| `EXTREME_SIGNAL` | ±1.8 |

### Logica di transizione

**Isteresi asimmetrica** — le soglie di ingresso e uscita da un regime non
coincidono. Per uscire da `expansion` lo score deve scendere sotto
`THRESHOLD_UP - HYSTERESIS = +0.3` per due mesi consecutivi. Questo rende
il sistema stabile attorno alle soglie ed evita oscillazioni continue.

**Conferma a due mesi** — una transizione di regime si concretizza solo se
il segnale è presente per due mesi consecutivi. Il sistema mantiene un
contatore di conferma (`counter`) e un regime pendente (`pending`). Se il
segnale torna coerente col regime attuale prima del secondo mese, il
contatore si azzera.

**Segnali estremi** — se lo score supera ±1.8 (vicino al clip di ±2),
la transizione è immediata senza attendere la conferma. Questi segnali
indicano condizioni di stress o euforia eccezionale che non possono essere
ignorati per due mesi.

### Stato del regime

Per ogni pillar il sistema mantiene:

| Campo | Tipo | Descrizione |
|---|---|---|
| `regime` | string | Regime corrente: expansion / neutral / contraction |
| `score` | float | Score grezzo del pillar (media z-score con inversione) |
| `score_ema` | float | Score dopo EWM — driver della regime detection |
| `counter` | int | Mesi consecutivi con segnale verso `pending` |
| `pending` | string | Regime verso cui si sta accumulando conferma |

### Lettura della tendenza in dashboard

La combinazione di `regime`, `counter` e `pending` determina tre stati
di tendenza leggibili senza ulteriori calcoli:

| Condizione | Tendenza |
|---|---|
| `pending` è None | Stabile — nessuna pressione di cambiamento |
| `pending` ≠ regime e `counter == 1` | Sotto pressione — segnale debole verso `pending` |
| `counter == CONFIRM_MONTHS - 1` | Transizione imminente — conferma al prossimo mese |

---

## Allocazione del Capitale

### Proxy degli asset class

| Asset Class | Proxy | Note |
|---|---|---|
| Equity | SPY | S&P 500 ETF |
| Bond | IEF | 7-10Y Treasury ETF |
| Commodities | DBC | Broad commodities ETF |
| Cash | BIL | 1-3 mese T-Bill ETF |

I pesi neutri, i vincoli min/max e il proxy sono configurati per asset
nella tabella `asset_classes`.

### Matrice di aggiustamento

Per ogni combinazione `(pillar, regime)` è definito un delta di allocazione
per ogni asset class. I delta sono salvati nella tabella
`allocation_adjustments` e modificabili senza deploy.

Schema della tabella:

| Campo | Tipo | Descrizione |
|---|---|---|
| `pillar` | string | Growth / Inflation / Policy / Risk |
| `regime` | string | expansion / neutral / contraction |
| `asset` | string | Equity / Bond / Commodities / Cash |
| `delta` | float | Variazione percentuale rispetto al peso neutro |

Vincolo: ogni riga `(pillar, regime, asset)` è unica. I delta per regime
`neutral` sono convenzionalmente zero — nessun aggiustamento quando il
pillar non dà un segnale direzionale.

Valori indicativi iniziali (da calibrare empiricamente):

| Pillar | Regime | Equity | Bond | Commodities | Cash |
|---|---|---|---|---|---|
| Growth | expansion | +8% | -5% | +3% | -6% |
| Growth | contraction | -8% | +5% | -3% | +6% |
| Inflation | expansion | -5% | -8% | +10% | +3% |
| Inflation | contraction | +3% | +5% | -8% | 0% |
| Policy | expansion | +6% | +5% | 0% | -11% |
| Policy | contraction | -6% | -5% | 0% | +11% |
| Risk | expansion | +5% | -3% | +2% | -4% |
| Risk | contraction | -8% | +5% | -2% | +5% |

Nota: ogni riga deve sommare a zero — i delta sono spostamenti relativi
tra asset, non incrementi assoluti.

### Formula di allocazione target

```
coherence  = 1 - (n_neutral / 4) × coherence_factor
total_delta[asset] = Σ delta(pillar, regime, asset)  per tutti i pillar
target[asset] = neutral_weight[asset] + total_delta[asset] × coherence
```

**Coefficiente di coerenza** — quando più pillar sono in `neutral` il segnale
complessivo è misto e l'intensità degli aggiustamenti si riduce. Con tutti
e 4 i pillar in regime attivo il coefficiente è 1.0; con tutti in `neutral`
scende a `1 - coherence_factor`. Il valore di `coherence_factor` (default 0.5)
è configurabile in `allocation_parameters`.

Dopo il calcolo del target vengono applicati:

1. **Vincoli min/max** per asset (`min_weight` e `max_weight` da `asset_classes`)
2. **Riscalatura a 100%** per garantire che i pesi sommino esattamente a 100

### Smoothing dell'allocazione

L'allocazione effettiva non salta direttamente al target ma si avvicina
gradualmente mese per mese:

```
effective[t] = effective[t-1] + allocation_alpha × (target[t] - effective[t-1])
```

Con `allocation_alpha = 0.3` (configurabile in `allocation_parameters`).
Questo crea un doppio buffer contro il whipsawing: il regime cambia lentamente
(conferma a 2 mesi), e anche quando cambia l'allocazione si muove
gradualmente verso il nuovo target.

La storia di `target` ed `effective` viene salvata mensilmente in
`allocation_history` per consentire analisi retrospettive e backtest.

---

## Configurazione su database

Tutta la configurazione è su DB e modificabile senza deploy.

| Tabella | Contenuto |
|---|---|
| `macro_indicators` | Ticker FRED con source e frequency |
| `processed_indicators` | Trasformazioni, resample, z-score params, flag `invert` |
| `pillars` + `pillar_components` | Definizione pillar e loro indicatori |
| `macro_regimes` | Score, score_ema, regime, counter, pending per pillar × mese |
| `asset_classes` | Pesi neutri, min/max weight, proxy symbol, display order |
| `allocation_adjustments` | Matrice delta per pillar × regime × asset |
| `allocation_parameters` | smoothing.alpha, allocation.alpha, coherence.factor |
| `allocation_history` | Target ed effective per asset × mese |

### Parametri in `allocation_parameters`

| Chiave | Default | Descrizione |
|---|---|---|
| `smoothing.alpha` | 0.4 | Alpha EWM sullo z-score dei pillar |
| `allocation.alpha` | 0.3 | Alpha smoothing allocazione mensile |
| `coherence.factor` | 0.5 | Intensità riduzione per pillar neutral |

---

## Flusso mensile

```
1. Ingestion nuovi dati FRED / Yahoo Finance
2. process_indicator() per ogni indicatore
      → smoothing grezzo → z-score → clip → EMA → salva in macro_processed
3. compute_pillars()
      → aggrega z_ema per pillar con inversione semantica
      → regime detection con isteresi e conferma
      → salva in macro_regimes
4. compute_target_allocation()
      → legge regimi correnti da macro_regimes
      → applica matrice di aggiustamento con coefficiente di coerenza
      → applica vincoli min/max e riscala
5. compute_effective_allocation()
      → smoothing EWM verso target
6. Presentazione all'utente per approvazione manuale
7. save_allocation() → salva in allocation_history
```

---

## Requisiti di trasparenza (anti-black-box)

Il sistema deve essere comprensibile senza leggere il codice.
La dashboard deve esporre in ogni momento:

| Informazione | Dove mostrarla |
|---|---|
| Score EMA corrente per ogni pillar | Dashboard macro |
| Regime corrente per ogni pillar | Dashboard macro, in evidenza |
| Tendenza regime (stabile / sotto pressione / imminente) | Dashboard macro |
| Mesi consecutivi nel regime corrente (`counter`) | Dashboard macro |
| Portafoglio target calcolato | Dashboard macro |
| Portafoglio effettivo corrente | Dashboard macro |
| Differenza target vs effettivo | Dashboard macro (trigger per ribilanciamento) |
| Delta applicati per pillar × asset | Dettaglio allocazione |

Ogni cambio di regime deve essere giustificabile: *"il regime di Growth è
passato da neutral a expansion perché lo score EMA è rimasto sopra +0.5
per due mesi consecutivi (Gennaio: +0.62, Febbraio: +0.71)"*.

---

## Validazione necessaria (prima del go live)

- [ ] Calibrazione empirica matrice di aggiustamento (IC su 2007–2017)
- [ ] Scelta `smooth_window` e `ema_alpha` ottimali su training period
- [ ] Test di reazione agli shock (2008, 2020, 2022)
- [ ] Verifica comportamento nei tre regimi per pillar sul validation set
- [ ] Paper trading su almeno un ciclo mensile completo