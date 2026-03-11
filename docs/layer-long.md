# Layer Long — Documentazione

## Responsabilità
Analisi macroeconomica continua e riallocazione strategica del capitale
sulla base del regime di mercato corrente. Opera con cadenza mensile (dati EOM).

## Stato attuale
Sviluppo avanzato. Componenti implementate:
- [x] Selezione e configurazione indicatori
- [x] Ingestion dei dati
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
Indicatori raw
     │
     ▼
  Ingestion          (services/ingest/)
     │
     ▼
  Normalizzazione    z-score con clipping
     │
     ▼
  Pillar Score       (services/pillars/)
     │
     ▼
  MacroScore         regime detection
     │
     ▼
  Sensitivity Matrix × Pillar Scores
     │
     ▼
  Adjustment Weights  (normalizzati, turnover cap 20%)
     │
     ▼
  Portafoglio ribilanciato  (mensile, EOM)
```

---

## Normalizzazione

Ogni indicatore viene normalizzato tramite z-score con clipping simmetrico:

```
z_clipped = min( max(z, -L), +L )
```

Il clipping evita che outlier estremi distorcano il segnale composito.
Il valore di L è configurabile per ogni indicatore.

---

## I quattro Pillar

### Growth — forza del ciclo economico reale
| Indicatore | Ticker | Trasformazione |
|---|---|---|
| PMI Manifatturiero (ISM) | ISM | z_clipped |
| GDP YoY | GDP_YoY | z_clipped |
| Industrial Production YoY | INDPRO_YoY | z_clipped |

```
GrowthScore = mean( z(PMI), z(GDP_YoY), z(INDPRO_YoY) )
```

### Inflation — pressione inflattiva realizzata e attesa
| Indicatore | Ticker | Trasformazione |
|---|---|---|
| CPI YoY | CPI_YoY | z_clipped |
| PPI YoY | PPI_YoY | z_clipped |
| 5Y Breakeven Inflation | T5YIE | z_clipped |

```
InflationScore = mean( z(CPI_YoY), z(PPI_YoY), z(T5YIE) )
```

### Policy — stance della banca centrale
| Indicatore | Ticker | Trasformazione |
|---|---|---|
| Fed Funds Rate | FEDFUNDS | z_clipped |
| Yield Curve (10Y–2Y) | YieldCurve | z_clipped |
| Variazione policy rate | ΔFEDFUNDS | z_clipped |

```
PolicyScore = mean( z(FEDFUNDS), z(YieldCurve), z(ΔFEDFUNDS) )
```

Nota: segni coerenti — rialzi e inversione della curva = restrittivo (score negativo).

### Risk — stress finanziario e risk aversion
| Indicatore | Ticker | Trasformazione |
|---|---|---|
| Credit Spread | CreditSpread | z_clipped |
| VIX | VIX | z_clipped |
| Financial Conditions Index | FCI | z_clipped |

```
RiskScore = mean( z(CreditSpread), z(VIX), z(FCI) )
```

---

## MacroScore e Regime Detection

```
MacroScore = 0.3 * Growth - 0.3 * Inflation - 0.2 * Policy - 0.2 * Risk
```

| MacroScore | Regime |
|---|---|
| > +0.5 | Espansione |
| >= 0 e <= +0.5 | Ripresa |
| >= -0.5 e < 0 | Rallentamento |
| < -0.5 | Recessione |

---

## Allocazione del Capitale

### Portafoglio neutro (baseline)
| Asset Class | Peso neutro |
|---|---|
| Equity | 40% |
| Bond | 35% |
| Commodities | 15% |
| FX (USD) | 10% |

### Matrice di sensibilità (fissa)
Definisce la direzione dell'impatto di ogni pillar su ogni asset class:

| Asset | Growth | Inflation | Policy | Risk |
|---|---|---|---|---|
| Equity | + | – | – | – |
| Bond | – | – | + | + |
| Commodities | + | + | 0 | – |
| FX (USD) | – | – | + | + |

### Formula di adjustment
Per ogni asset class:

```
adjustment_asset = a1*GrowthScore + a2*InflationScore + a3*PolicyScore + a4*RiskScore
```

I coefficienti `a1..a4` riflettono segno e intensità della sensitivity matrix.
Esempio per Equity:

```
Equity_adj = +0.4*Growth - 0.3*Inflation - 0.2*Policy - 0.1*Risk
```

Vincoli:
- `peso_finale >= 0`
- `peso_finale <= max_asset_weight` (configurabile per asset)
- Pesi normalizzati a 100% prima dell'esecuzione

### Regole di stabilità
- Ribilanciamento mensile (dati EOM)
- Turnover massimo per mese: **20%**
- Se l'adjustment supera il cap di turnover, la variazione viene troncata e riscalata

---

## Validazione necessaria (prima del go live)
- [ ] Calibrazione della matrice di base sui dati storici
- [ ] Test di reazione agli shock (2008, 2020, 2022)
- [ ] Verifica comportamento nei quattro regimi
- [ ] Definizione di `max_asset_weight` per ogni asset class
- [ ] Paper trading su almeno un ciclo mensile completo