# Layer Long — Documentazione

## Responsabilità
Analisi macroeconomica continua e riallocazione strategica del capitale
sulla base del regime di mercato corrente. Opera con cadenza mensile.

## Stato attuale
Sviluppo avanzato. Componenti implementate:
- [x] Selezione e configurazione indicatori (su database)
- [x] Ingestion dei dati (FRED + Yahoo Finance)
- [x] Resample a frequenza mensile per serie DAILY/WEEKLY
- [x] Normalizzazione (z-score con clipping)
- [x] Calcolo dei pillar
- [x] MacroScore e rilevamento regime
- [x] Allocazione del capitale
- [ ] Validazione: matrice di base da calibrare
- [ ] Validazione: reazione agli shock
- [ ] Validazione: comportamento in differenti regimi
- [ ] Paper trading / go live

Gestione: **manuale** — il sistema calcola e propone, l'utente approva.

---

## Pipeline

```
Indicatori raw (FRED / Yahoo Finance)
     │
     ▼
  Ingestion              (services/ingest/)
     │
     ▼
  Resample mensile       resample("MS").mean()  ← solo per serie DAILY/WEEKLY
     │
     ▼
  Trasformazione         yoy | level | delta
     │
     ▼
  Z-score + clipping     rolling(60).mean/std, clip ±3
     │
     ▼
  Pillar Score           (services/pillars/)
     │
     ▼
  MacroScore             weighted sum + regime detection
     │
     ▼
  Sensitivity Matrix × Pillar Scores
     │
     ▼
  Adjustment Weights     (K=5%, cap ±10%)
     │
     ▼
  Portafoglio ribilanciato  (mensile)
```

---

## Indicatori e trasformazioni

Tutti i processed indicator hanno data di inizio mese (convenzione FRED).
Le serie non-mensili vengono resampelate a `MS` (month start) con media prima
di qualsiasi trasformazione.

### Convenzione nomi
- Serie native mensili: nome invariato (es. `FEDFUNDS`, `CPI_YOY`)
- Serie resampelate da DAILY/WEEKLY: suffisso `_M` (es. `VIXCLS_M`, `T10Y2Y_M`)

---

## I quattro Pillar

### Growth — forza del ciclo economico reale

| Processed indicator | Sorgente | Freq. raw | Trasformazione |
|---|---|---|---|
| `CUMFNS` | CUMFNS | MONTHLY | level (diff 1) |
| `INDPRO_YOY` | INDPRO | MONTHLY | yoy % change |
| `W875RX1_YOY` | W875RX1 | MONTHLY | yoy % change |

```
GrowthScore = mean( z(CUMFNS), z(INDPRO_YOY), z(W875RX1_YOY) )
```

### Inflation — pressione inflattiva realizzata e attesa

| Processed indicator | Sorgente | Freq. raw | Trasformazione |
|---|---|---|---|
| `CPI_YOY` | CPIAUCSL | MONTHLY | yoy % change |
| `PPIACO_YOY` | PPIACO | MONTHLY | yoy % change |
| `EXPINF5YR` | EXPINF5YR | MONTHLY | level (diff 1) |

```
InflationScore = mean( z(CPI_YOY), z(PPIACO_YOY), z(EXPINF5YR) )
```

### Policy — stance della banca centrale

| Processed indicator | Sorgente | Freq. raw | Trasformazione |
|---|---|---|---|
| `FEDFUNDS` | FEDFUNDS | MONTHLY | level (diff 1) |
| `FEDFUNDS_DELTA` | FEDFUNDS | MONTHLY | delta (diff 1) |
| `T10Y2Y_M` | T10Y2Y | DAILY → resample MS | level (diff 1) |

```
PolicyScore = mean( z(FEDFUNDS), z(FEDFUNDS_DELTA), z(T10Y2Y_M) )
```

Nota: rialzi del tasso e inversione della curva producono score negativo (politica restrittiva).

### Risk — stress finanziario e risk aversion

| Processed indicator | Sorgente | Freq. raw | Trasformazione |
|---|---|---|---|
| `BAA10Y_M` | BAA10Y | DAILY → resample MS | level (diff 1) |
| `VIXCLS_M` | VIXCLS | DAILY → resample MS | level (diff 1) |
| `NFCI_M` | NFCI | WEEKLY → resample MS | level (diff 1) |

```
RiskScore = mean( z(BAA10Y_M), z(VIXCLS_M), z(NFCI_M) )
```

---

## MacroScore e Regime Detection

```
MacroScore = 0.3 * Growth - 0.3 * Inflation - 0.2 * Policy - 0.2 * Risk
```

| MacroScore | Regime |
|---|---|
| > +0.5 | Espansione |
| > 0.0 | Ripresa |
| > -0.5 | Rallentamento |
| ≤ -0.5 | Recessione |

---

## Allocazione del Capitale

### Portafoglio neutro (baseline)
| Asset Class | Peso neutro | Peso massimo | Proxy |
|---|---|---|---|
| Equity | 50% | 70% | SPY |
| Bond | 30% | 55% | IEF |
| Commodities | 10% | 30% | DBC |
| Cash | 10% | 30% | BIL |

### Matrice di sensibilità

| Asset | Growth | Inflation | Policy | Risk |
|---|---|---|---|---|
| Equity | +1.0 | -0.5 | -0.5 | -1.0 |
| Bond | -0.5 | -1.0 | +1.0 | +0.5 |
| Commodities | +0.5 | +1.0 | -0.5 | -0.5 |
| Cash | -0.5 | 0.0 | 0.0 | +1.0 |

### Parametri engine

| Parametro | Valore | Descrizione |
|---|---|---|
| `scale_factor_k` | 0.05 | Fattore di scala per il tilt (5%) |
| `max_abs_delta` | 0.10 | Cap assoluto deviazione dal peso neutro (±10%) |

### Formula di adjustment
```
raw_tilt[asset] = Σ f(pillar_score) × sensitivity[pillar][asset]
delta[asset]    = raw_tilt[asset] × K  (poi mean-centered e capped a ±MAX_ABS)
weight[asset]   = neutral[asset] + delta[asset]  (normalizzati a 100%)
```

dove `f(x)` è una saturazione lineare: `f(x) = x/2` per |x| ≤ 2, ±1 altrimenti.

---

## Configurazione su database

Tutta la configurazione è su DB e modificabile senza deploy.
Seed iniziale: `python -m app.scripts.seed_config`

| Tabella | Contenuto |
|---|---|
| `macro_indicators` | Ticker FRED con source e frequency |
| `processed_indicators` | Trasformazioni + resample + z-score params |
| `pillars` + `pillar_components` | Definizione pillar e loro indicatori |
| `composite_scores` + `composite_score_weights` | MacroScore e pesi pillar |
| `regime_thresholds` | Soglie di regime per score |
| `asset_classes` | Pesi neutri, max weight, proxy symbol |
| `sensitivity_coefficients` | Matrice di sensibilità pillar × asset |
| `allocation_parameters` | K, MAX_ABS |

---

## Validazione necessaria (prima del go live)
- [ ] Calibrazione della matrice di sensibilità sui dati storici
- [ ] Test di reazione agli shock (2008, 2020, 2022)
- [ ] Verifica comportamento nei quattro regimi
- [ ] Paper trading su almeno un ciclo mensile completo
