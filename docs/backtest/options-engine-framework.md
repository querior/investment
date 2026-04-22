# Options Engine Framework
> Documento di lavoro — sintesi della sessione di design

---

## 1. Framework di Selezione Strategica

### Processo Decisionale in 3 Livelli
Il sistema seleziona la strategia ottimale combinando tre input sequenziali:

1. **Outlook direzionale** — bias rialzista, ribassista o neutrale
2. **Regime di volatilità implicita** — IV Rank / IV Percentile come filtro primario
3. **Greche** — Delta, Vega, Theta, Gamma come parametri di fine-tuning

### Regola Base IV
| IV Rank | Interpretazione | Approccio |
|---|---|---|
| < 30% | Opzioni economiche | Comprare volatilità (long premium) |
| 30–50% | Neutro | Spread direzionali bilanciati |
| > 50% | Opzioni care | Vendere volatilità (short premium) |

---

## 2. Strategie Core a Rischio Controllato

Tutte le strategie adottate dall'Engine hanno **perdita massima definita** — nessuna posizione naked. Organizzate per famiglia operativa.

---

### Famiglia 1 — Spread Direzionali a Debito
*Paghi un premio netto. Profitto se il mercato si muove nella direzione attesa.*

#### Bull Call Spread
- **Struttura:** Buy Call strike basso + Sell Call strike alto (stesso mese)
- **Quando:** bias rialzista + IV bassa (debit contenuto)
- **Max gain:** differenza strike − premio pagato
- **Max loss:** premio pagato
- **Greche:** Delta positivo, Vega positivo, Theta negativo
- **Regime ideale:** Espansione / Zona A IV bassa

#### Bear Put Spread
- **Struttura:** Buy Put strike alto + Sell Put strike basso (stesso mese)
- **Quando:** bias ribassista + IV bassa
- **Max gain:** differenza strike − premio pagato
- **Max loss:** premio pagato
- **Greche:** Delta negativo, Vega positivo, Theta negativo
- **Regime ideale:** Recessione / Zona A IV bassa con trend down

---

### Famiglia 2 — Spread Direzionali a Credito
*Incassi un premio netto. Profitto se il mercato NON raggiunge lo strike venduto.*

#### Bull Put Spread (Credit Spread)
- **Struttura:** Sell Put strike alto + Buy Put strike basso (stesso mese)
- **Quando:** bias rialzista o neutrale + IV alta (credito elevato)
- **Max gain:** credito incassato
- **Max loss:** differenza strike − credito
- **Greche:** Delta positivo, Vega negativo, Theta positivo
- **Regime ideale:** Espansione o Rallentamento / IV > 40%

#### Bear Call Spread (Credit Spread)
- **Struttura:** Sell Call strike basso + Buy Call strike alto (stesso mese)
- **Quando:** bias ribassista o neutrale + IV alta
- **Max gain:** credito incassato
- **Max loss:** differenza strike − credito
- **Greche:** Delta negativo, Vega negativo, Theta positivo
- **Regime ideale:** Rallentamento / Recessione con IV elevata

---

### Famiglia 3 — Strategie Long Volatilità
*Scommetti sul movimento, non sulla direzione. Profitto se il mercato si muove molto in qualsiasi direzione.*

#### Long Straddle
- **Struttura:** Buy Call ATM + Buy Put ATM (stesso strike)
- **Quando:** IV bassa, evento imminente, forte movimento atteso
- **Max gain:** illimitato
- **Max loss:** premio totale pagato
- **BEP:** Strike ± Premio totale
- **Greche:** Delta neutro, Vega molto positivo, Theta molto negativo, Gamma alto
- **Regime ideale:** Zona C / IV Rank < 20% / squeeze attivo

#### Long Strangle
- **Struttura:** Buy Call OTM + Buy Put OTM (strike diversi)
- **Quando:** IV bassa, grande volatilità attesa ma timing incerto
- **Max gain:** illimitato
- **Max loss:** premio totale (inferiore allo Straddle)
- **BEP:** Call strike + totale / Put strike − totale (zona più ampia)
- **Greche:** Delta neutro, Vega positivo, Theta negativo
- **Regime ideale:** Zona C / IV Rank < 25% / breakout atteso su range

---

### Famiglia 4 — Strategie Short Volatilità
*Scommetti sulla stabilità. Profitto se il mercato rimane in un range. Richiedono gestione attiva.*

#### Short Straddle
- **Struttura:** Sell Call ATM + Sell Put ATM (stesso strike)
- **Quando:** IV molto alta, mercato fortemente laterale, gestione attiva garantita
- **Max gain:** premio totale incassato
- **Max loss:** teoricamente illimitato → **usare solo con hedge o size minima**
- **BEP:** Strike ± Premio totale
- **Greche:** Delta neutro, Vega molto negativo, Theta molto positivo
- **Regime ideale:** Zona D / IV Rank > 70% / post-evento (vol crush atteso)
- **⚠️ Rischio:** posizione non a perdita definita — l'Engine limita la size al 25% del normale

#### Short Strangle
- **Struttura:** Sell Call OTM + Sell Put OTM (strike diversi)
- **Quando:** IV alta, range laterale consolidato, gestione attiva
- **Max gain:** credito incassato
- **Max loss:** teoricamente illimitato → **usare solo con hedge o size minima**
- **BEP:** Call strike + totale / Put strike − totale
- **Greche:** Delta neutro, Vega negativo, Theta positivo
- **Regime ideale:** Zona D / IV Rank > 60%
- **⚠️ Rischio:** come Short Straddle — size ridotta, stop stretto, mai in regime Recessione

---

### Famiglia 5 — Strutture Combinate a Rischio Definito
*Combinano vendita di volatilità con protezione incorporata. Massima perdita sempre definita.*

#### Iron Condor
- **Struttura:** Bull Put Spread + Bear Call Spread (4 gambe)
  - Sell Put OTM / Buy Put più OTM
  - Sell Call OTM / Buy Call più OTM
- **Quando:** mercato laterale + IV alta → profitto dal decadimento temporale
- **Max gain:** credito netto incassato
- **Max loss:** larghezza ala − credito netto
- **Zona profitto:** tra i due short strike
- **Greche:** Delta neutro, Vega negativo, Theta positivo, Gamma negativo
- **Regime ideale:** Zona D / IV Rank > 50% / ADX < 20

#### Iron Butterfly
- **Struttura:** Sell Call ATM + Sell Put ATM + Buy Call OTM + Buy Put OTM
- **Quando:** mercato fortemente laterale, prezzo esattamente ATM, IV molto alta
- **Max gain:** credito netto (superiore all'Iron Condor)
- **Max loss:** larghezza ala − credito
- **Zona profitto:** molto stretta intorno allo strike centrale
- **Greche:** Delta neutro, Vega molto negativo, Theta molto positivo
- **Regime ideale:** Zona D / IV Rank > 65% / prezzo "inchiodato" su livello chiave
- **Differenza da IC:** guadagno potenziale maggiore, ma zona di profitto molto più stretta

---

### Tabella Riepilogativa

| Strategia | Direzione | IV ideale | Max Loss | Max Gain | Theta | Vega |
|---|---|---|---|---|---|---|
| Bull Call Spread | Rialzista | Bassa | Premio pagato | Limitato | ➖ | ➕ |
| Bear Put Spread | Ribassista | Bassa | Premio pagato | Limitato | ➖ | ➕ |
| Bull Put Spread | Rialzista/Neutro | Alta | Larghezza − credito | Credito | ➕ | ➖ |
| Bear Call Spread | Ribassista/Neutro | Alta | Larghezza − credito | Credito | ➕ | ➖ |
| Long Straddle | Neutro (movimento) | Molto bassa | Premio totale | Illimitato | ➖➖ | ➕➕ |
| Long Strangle | Neutro (movimento) | Bassa | Premio totale | Illimitato | ➖ | ➕ |
| Short Straddle ⚠️ | Neutro (stabilità) | Molto alta | Illimitato* | Premio totale | ➕➕ | ➖➖ |
| Short Strangle ⚠️ | Neutro (stabilità) | Alta | Illimitato* | Premio totale | ➕ | ➖ |
| Iron Condor | Neutro (stabilità) | Alta | Larghezza − credito | Credito | ➕ | ➖ |
| Iron Butterfly | Neutro (stabilità) | Molto alta | Larghezza − credito | Credito alto | ➕➕ | ➖➖ |

> ⚠️ Short Straddle e Short Strangle: perdita teoricamente illimitata. L'Engine le ammette solo con size ≤ 25% e stop loss stretto. In regime Recessione o Crisi sono **sempre escluse**.

---

## 3. Integrazione con Analisi Tecnica

I segnali tecnici guidano **quando** e **dove** posizionarsi:

- **Squeeze di Bollinger** (BB Width ai minimi + IV bassa) → setup ideale per long vol
- **Triangoli / Wedge** → breakout atteso → Strangle con strike oltre i livelli del pattern
- **S/R chiave** → zona di decisione → Straddle ATM
- **Pre-evento** → RSI neutro, MACD piatto, volumi bassi → entrata prima dello spike IV

### Timing con le Greche
- **Delta neutro** all'ingresso → no bias direzionale
- **Vega positivo** → entra con IV bassa
- **Gamma alto** → vicino alla scadenza, ogni movimento accelera il gain
- **Theta** → il nemico, il timing tecnico è critico

---

## 4. Architettura del Backtest Engine

### Stack Tecnologico
- **Data:** `pandas`, `numpy`, `yfinance`, `mibian`, `py_vollib`
- **Indicatori:** `pandas_ta`, `ta-lib`
- **Backtest:** `vectorbt` (principale), `backtrader` (event-driven)
- **Ottimizzazione:** `optuna` (Bayesian), `scipy.optimize`
- **Analisi risultati:** `quantstats`, `plotly`

### Struttura Modulare
```
optimizer/
├── data/         → loader + features (IV rank, HV, squeeze, RSI)
├── engine/       → strategy + backtest loop
├── optimizer/    → objective function + walk-forward
└── analysis/     → report + grafici
```

### Ottimizzazione con Optuna
Preferito al Grid Search per spazi parametrici > 4 dimensioni.
TPE Sampler + pruning → converge in ~500 trial invece di 86.000.

---

## 5. Segnali di Ingresso

### Segnali Primari (tutti e tre necessari)
1. **IV Rank < 30%** + IV/HV30 < 1.0 + IV Percentile < 25%
2. **Squeeze attivo** → BB Width < percentile(20) + ATR14 in calo + TTM Squeeze
3. **Neutralità direzionale** → RSI [40,60] + MACD piatto + ADX < 25

### Score di Ingresso Composito
```python
Q_entry = w1*(100 - IV_rank)       # peso 30 — IV regime
        + w2*(1 - IV/HV_ratio)     # peso 20 — IV/HV
        + w3*squeeze_intensity     # peso 20 — compressione BB
        + w4*RSI_neutrality        # peso 15 — neutralità
        + w5*DTE_score             # peso 10 — DTE ottimale
        + w6*volume_ratio          # peso  5 — volume basso
```

**Soglie operative:** > 75 full size / 60–74 size ridotta / < 60 no entry

### Segnali di NON Ingresso
- IV Rank > 50%, ADX > 30, RSI > 70 o < 30
- Earnings < 15gg, Spread bid/ask > 10%, Open Interest insufficiente

---

## 6. Classificazione del Regime Macro — Layer 0

### I 4 Quadranti (Crescita × Inflazione)
```
                  IV BASSA (<30%)        IV ALTA (>50%)
DIREZIONALE   →   ZONA A                 ZONA B
(ADX > 25)        Long vol + bias        Credit spread dir.

LATERALE      →   ZONA C                 ZONA D
(ADX < 25)        Straddle / Strangle    Iron Condor / Short Strangle
```

### I 5 Regimi Macro
| Regime | Crescita | Inflazione | Approccio |
|---|---|---|---|
| **Goldilocks / Espansione** | positiva | in calo | Risk-on pieno, full size |
| **Surriscaldamento** | positiva | in salita | Risk-on selettivo |
| **Rallentamento** | in calo | — | Size -25%, credit spread |
| **Recessione** | negativa | — | Solo perdita definita, size -50% |
| **Stagflazione** | negativa | in salita | Regime peggiore, DTE corto |
| **Crisi** | — | — | Stop speculazione, solo hedge |

### Indicatori Macro Chiave
- **Crescita:** PMI, Yield Curve (10Y-2Y), LEI, HY Spread
- **Stress:** VIX, HY OAS, % titoli sopra MA200
- **Transizione:** PMI sotto 48 per 2 mesi + Yield Curve invertita > 3 mesi + LEI negativo → Recessione

---

## 7. Matrice Strategia per Regime

| Macro | Zona | IV | Trend | Strategia | Size | DTE |
|---|---|---|---|---|---|---|
| Espansione | A | bassa | up | Bull Call Spread | 100% | 30–40 |
| Espansione | C | bassa | neutro | Long Straddle | 100% | 35–40 |
| Espansione | D | alta | neutro | Iron Condor | 100% | 30–45 |
| Rallentamento | A | bassa | up | Bull Put Spread | 75% | 30–35 |
| Rallentamento | C | bassa | neutro | Long Strangle | 50% | max 35gg |
| Rallentamento | D | alta | neutro | Iron Condor (ali larghe) | 75% | 30–40 |
| Recessione | A | — | down | Bear Put Spread | 75% | — |
| Recessione | D | alta | neutro | Iron Condor (cauto) | 25% | — |
| Stagflazione | * | alta | — | Credit Spread o SKIP | 50% | 25–30 |
| Crisi | * | molto alta | — | SKIP / Long Put hedge | 0% | — |

---

## 8. Segnali di Uscita — Gerarchia dei Trigger

```
PRIORITÀ    TRIGGER                          AZIONE
────────────────────────────────────────────────────────────
  1°        Cambio regime macro              Exit totale forzata
  2°        VIX spike > 40% / HY spread      Exit totale forzata
  3°        Vol crush post-evento            Exit entro 1 ora
  4°        Stop loss aggiustato al regime   Exit totale
  5°        DTE sotto soglia (21gg)          Exit totale
  6°        IV spike (short vol > 75%)       Exit totale
  7°        Segnale tecnico inversione       Exit parziale/totale
  8°        Profit target                    Exit scalata
  9°        Lato vincente > 80% max          Exit parziale + conversione
```

### Stop Loss per Strategia
| Strategia | Stop | Moltiplicatore Regime |
|---|---|---|
| Long Straddle / Strangle | -100% premio | Espansione 1.0x / Recessione 0.7x |
| Bull/Bear Spread | -75% | — |
| Iron Condor / Short Strangle | -200% credito | — |

### Profit Target per Regime
| Strategia | Espansione | Rallentamento | Recessione |
|---|---|---|---|
| Long vol | 75% | 60% | 50% |
| Credit spread | 50% | 40% | 30% |
| Debit direzionale | 100% | 75% | 60% |

---

## 9. Pricing di Entrata

### Fair Value vs Mercato
```python
edge = theoretical_value(σ=HV30) - market_price
# edge > 0  → stai comprando sotto fair value
# edge > 10% → entry di qualità
```

### IV/HV Ratio
| Ratio | Rating |
|---|---|
| < 0.80 | Eccellente — compra |
| 0.80–0.90 | Buono |
| 0.90–1.00 | Neutro |
| > 1.00 | Caro — riduci size o evita |

### Breakeven Raggiungibile
```python
move_1sigma = spot * HV30 * sqrt(DTE/252)
# BEP entro 1 sigma → raggiungibile
# BEP < 0.85 sigma  → OTTIMO
# BEP > 1.5 sigma   → EVITA
```

### Bid/Ask — Costo Nascosto
- < 5% del mid → Ottimo
- 5–15% → Accettabile
- > 15% → Evita (soprattutto su 4 gambe come IC)

### Score Pricing Composito
```
> 75   → size piena
60–74  → size 75%
45–59  → size 50%
< 45   → no entry
```

---

## 10. Caso Reale — IWM

### Long Strangle (IV bassa, squeeze)
```
Spot: 195.50 / HV30: 18.5% / IV: 16.2% / IV Rank: 22% / DTE: 35

Strike: 185 Put + 205 Call  (±75% di 1 sigma)
Premio totale reale: 2.58$
BEP: 182.42 ↔ 207.58  (entrambi sotto 1 sigma ✅)
Edge teorico: +13.9%
Score finale: 35.1 (regime Rallentamento) → size 50%

Exit: PT 60% / SL -75% / DTE exit 21gg
```

### Iron Condor (IV alta, laterale)
```
Spot: 195.50 / HV30: 18.5% / IV: 22.8% / IV Rank: 58% / DTE: 35

Struttura: 179p/184p/207c/212c
Credito reale: 1.25$ / Max loss: 3.75$
BEP: 182.75 ↔ 208.25  (±6.5%)
IV/HV ratio: 1.335  → vendendo vol al 33% sopra HV → OTTIMO
Edge: +40.4%
Score finale: 51.6 (regime Rallentamento) → size 50%

Exit: PT 50% credito / SL 200% credito / DTE exit 21gg
```

---

## 11. Adjustment e Roll — Iron Condor

### Zone di Allerta (basate su ATR14)
```
Verde:   spot lontano > 2 ATR dagli short strike  → no action
Gialla:  spot a 1–2 ATR dagli short strike        → monitora daily
Rossa:   spot a < 0.5 ATR dagli short strike      → adjustment oggi
```

### Trigger di Adjustment
- Delta short leg > 0.35
- P&L ala > -150% del credito incassato
- IV Rank > 75% → chiudi tutto
- DTE < 21 → chiudi tutto, no roll

### Opzioni di Adjustment (in ordine)
1. **Roll verticale** → stesso mese, strike più lontano (DTE > 30)
2. **Roll temporale** → mese successivo, più credito (DTE 21–30)
3. **Chiusura parziale** → chiudi ala in stress, tieni lato sano → converte in spread direzionale
4. **Chiusura totale** → se IV spike, DTE < 21, perdita > 2x credito, cambio regime

### Regole del Roll
- Mai rollare in perdita netta (roll deve essere a credito o BE)
- Max 2 roll per posizione
- Dopo il roll, distanza spot-short ≥ 1 ATR
- Credito netto residuo sempre > 0

---

## 12. Portafoglio Rolling Cross-Asset

### Logica di Base
Invece di un trade singolo, un **nastro trasportatore continuo** di 3–4 posizioni su scadenze sfalsate di 15 giorni. Ogni posizione usa la strategia coerente con il regime del momento al suo ingresso.

### Selezione Titoli per Regime
| Regime | Titoli | Logica |
|---|---|---|
| Espansione | IWM, QQQ, XLK | Growth e tech beneficiano |
| Rallentamento | SPY, XLP, XLV | Large cap difensive reggono |
| Recessione | GLD, TLT, VXX | Oro, bond, volatilità salgono |
| Stagflazione | XLE, GLD, PDBC | Energia e commodities |

### Vantaggi
- **Diversificazione temporale** → scadenze diverse reagiscono in modo diverso agli shock
- **Theta costante** → sempre posizioni in decadimento attivo
- **Reattività graduale** → il cambio di regime ribilancia il portafoglio naturalmente

### Rischio Principale
Correlazione di crisi → tutti i titoli convergono a 1.0. Il Layer 0 macro gestisce questo: in regime Crisi il nastro si ferma, si apre solo protezione long put.

---

## 13. [WIP] Criteri di Selezione Titoli e Sizing Cross-Asset

> **Punto aperto — da sviluppare nella prossima sessione**

Temi da definire:
- Criteri quantitativi per la selezione dei titoli per ogni regime (correlazione, beta, liquidità opzioni)
- Logica di sizing tra posizioni diverse (Kelly, risk parity, volatility targeting)
- Come gestire la correlazione di portafoglio in tempo reale
- Ribilanciamento automatico al cambio di regime
- Numero ottimale di titoli per regime e massima esposizione per asset

---

*Documento generato dalla sessione di design — aggiornato progressivamente*
