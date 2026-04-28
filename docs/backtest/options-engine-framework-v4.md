# Options Engine Framework
> Documento di lavoro — versione 4 aggiornata

---

## Indice

- [Principio Fondante — Rischio Sempre Definito](#principio-fondante--rischio-sempre-definito)
- [1. Framework di Selezione Strategica](#1-framework-di-selezione-strategica)
- [2. Strategie Core a Rischio Controllato](#2-strategie-core-a-rischio-controllato)
  - [Famiglia 1 — Spread Direzionali a Debito](#famiglia-1--spread-direzionali-a-debito)
  - [Famiglia 2 — Spread Direzionali a Credito](#famiglia-2--spread-direzionali-a-credito)
  - [Famiglia 3 — Strategie Long Volatilità](#famiglia-3--strategie-long-volatilità)
  - [Famiglia 4 — Strutture Combinate a Rischio Definito](#famiglia-4--strutture-combinate-a-rischio-definito)
  - [Famiglia 5 — Strategie Avanzate a Rischio Definito](#famiglia-5--strategie-avanzate-a-rischio-definito)
  - [Tabella Riepilogativa](#tabella-riepilogativa)
- [3. Integrazione con Analisi Tecnica](#3-integrazione-con-analisi-tecnica)
- [4. Architettura del Backtest Engine](#4-architettura-del-backtest-engine)
- [5. Segnali di Ingresso](#5-segnali-di-ingresso)
- [6. Classificazione del Regime Macro — Layer 0](#6-classificazione-del-regime-macro--layer-0)
- [7. Matrice Strategia per Regime](#7-matrice-strategia-per-regime)
- [8. Segnali di Uscita — Gerarchia dei Trigger](#8-segnali-di-uscita--gerarchia-dei-trigger)
- [9. Pricing di Entrata](#9-pricing-di-entrata)
- [10. Caso Reale — IWM](#10-caso-reale--iwm)
- [11. Adjustment e Roll — Iron Condor](#11-adjustment-e-roll--iron-condor)
- [12. Portafoglio Rolling Cross-Asset *(WIP)*](#12-wip-portafoglio-rolling-cross-asset)
- [13. Criteri di Selezione Titoli e Sizing Cross-Asset *(WIP)*](#13-wip-criteri-di-selezione-titoli-e-sizing-cross-asset)
- [14. Pricing e Sizing in Relazione al Rischio](#14-pricing-e-sizing-in-relazione-al-rischio)
- [Changelog](#changelog)

---

## Principio Fondante — Rischio Sempre Definito

> **Tutte le strategie operative hanno perdita massima definita e nota al momento dell'ingresso. Nessuna posizione naked è ammessa in nessun regime, nessuna condizione di mercato, nessuna size.**

Questo è il vincolo architetturale dell'intero sistema. Non è una regola tra le altre — è il filtro che determina quali strategie esistono nel framework e quali no.

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

Tutte le strategie adottate dall'Engine hanno **perdita massima definita** — nessuna posizione naked, nessuna eccezione. Organizzate per famiglia operativa.

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

### Famiglia 4 — Strutture Combinate a Rischio Definito
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

### Famiglia 5 — Strategie Avanzate a Rischio Definito
*Strutture asimmetriche che combinano bias direzionale con vendita di volatilità. Perdita massima sempre definita.*

#### Calendar Spread
- **Struttura:** Sell opzione scadenza vicina + Buy stessa opzione scadenza lontana (stesso strike)
- **Quando:** mercato laterale atteso nel breve, IV bassa, nessun evento imminente sulla scadenza vicina
- **Max gain:** limitato (differenza di decadimento tra i due mesi)
- **Max loss:** premio netto pagato
- **Greche:** Delta neutro, Vega positivo, Theta positivo
- **Regime ideale:** Zona C / Rallentamento / IV bassa come alternativa economica allo Straddle

#### Jade Lizard
- **Struttura:** Sell Put OTM + Sell Call OTM + Buy Call più OTM (3 gambe)
- **Quando:** bias leggermente rialzista + IV alta; credito totale > larghezza ala call → rischio zero al rialzo
- **Max gain:** credito incassato
- **Max loss:** Put strike − credito totale (solo al ribasso)
- **Greche:** Delta leggermente positivo, Vega negativo, Theta positivo
- **Regime ideale:** Zona D / Espansione o Rallentamento / IV > 45%
- **Vantaggio vs IC:** meno gambe da gestire, elimina strutturalmente il rischio sul lato superiore

#### Reverse Jade Lizard
- **Struttura:** Sell Call OTM + Sell Put OTM + Buy Put più OTM (3 gambe)
- **Quando:** bias leggermente ribassista + IV alta; speculare alla Jade Lizard
- **Max gain:** credito incassato
- **Max loss:** solo al rialzo
- **Greche:** Delta leggermente negativo, Vega negativo, Theta positivo
- **Regime ideale:** Zona D / Rallentamento o Recessione / IV > 45%

#### Broken Wing Butterfly (BWB)
- **Struttura:** Butterfly asimmetrica — un'ala più larga dell'altra
  - Versione rialzista: Buy Call bassa / Sell 2 Call medie / Buy Call alta più lontana
- **Quando:** bias direzionale debole + costo vicino a zero o credito netto
- **Max gain:** limitato nella zona centrale
- **Max loss:** definita sul lato sfavorevole; lato favorevole a rischio zero se costruita a credito
- **Greche:** Delta leggero, Vega basso, Theta leggermente positivo
- **Regime ideale:** Zona A/C / Transizione tra regimi / IV media

#### Diagonal Spread
- **Struttura:** Buy opzione scadenza lontana strike basso + Sell opzione scadenza vicina strike alto
- **Quando:** bias direzionale moderato + vuoi ridurre il costo con vendita del mese vicino
- **Max gain:** limitato, aumenta rollando la gamba corta mese dopo mese
- **Max loss:** differenza tra costo della gamba lunga e credito incassato
- **Greche:** Delta moderato, Vega positivo, Theta leggermente positivo
- **Regime ideale:** Zona A / Espansione / DTE lungo (60–90gg sulla gamba lunga)

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
| Iron Condor | Neutro (stabilità) | Alta | Larghezza − credito | Credito | ➕ | ➖ |
| Iron Butterfly | Neutro (stabilità) | Molto alta | Larghezza − credito | Credito alto | ➕➕ | ➖➖ |
| Calendar Spread | Neutro (breve) | Bassa | Premio netto | Limitato | ➕ | ➕ |
| Jade Lizard | Leggermente rialzista | Alta | Limitato (solo ribasso) | Credito | ➕ | ➖ |
| Reverse Jade Lizard | Leggermente ribassista | Alta | Limitato (solo rialzo) | Credito | ➕ | ➖ |
| Broken Wing Butterfly | Direzionale debole | Media | Definita (un lato) | Limitato | ➕ | ➖ |
| Diagonal Spread | Direzionale moderato | Media | Definita | Limitato | ➕ | ➕ |

> ✅ Tutte le strategie hanno perdita massima definita. Le posizioni naked (Short Straddle, Short Strangle) sono **rimosse dal framework** in quanto incompatibili con il principio fondante del rischio controllato.

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
                  IV BASSA (<30%)              IV ALTA (>50%)
DIREZIONALE   →   ZONA A                       ZONA B
(ADX > 25)        Bull/Bear Spread             Credit Spread dir.
                  BWB / Diagonal               Jade / Rev. Jade Lizard

LATERALE      →   ZONA C                       ZONA D
(ADX < 25)        Long Straddle / Strangle     Iron Condor / Iron Butterfly
                  Calendar Spread              Jade Lizard
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
| Espansione | A | bassa | up | Broken Wing Butterfly | 100% | 30–40 |
| Espansione | A | media | up | Diagonal Spread | 100% | 60–90 |
| Espansione | C | bassa | neutro | Long Straddle | 100% | 35–40 |
| Espansione | D | alta | neutro | Iron Condor | 100% | 30–45 |
| Espansione | D | alta | neutro | Iron Butterfly | 100% | 30–45 |
| Espansione | D | alta | lieve up | Jade Lizard | 100% | 30–45 |
| Rallentamento | A | bassa | up | Bull Put Spread | 75% | 30–35 |
| Rallentamento | C | bassa | neutro | Long Strangle | 50% | max 35gg |
| Rallentamento | C | bassa | neutro | Calendar Spread | 75% | — |
| Rallentamento | D | alta | neutro | Iron Condor (ali larghe) | 75% | 30–40 |
| Rallentamento | D | alta | lieve down | Reverse Jade Lizard | 75% | 30–40 |
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
| Iron Condor / Iron Butterfly | -200% credito | — |
| Jade Lizard / Reverse | -200% credito | — |
| Calendar Spread / Diagonal | -50% premio | — |
| Broken Wing Butterfly | -100% rischio definito | — |

### Profit Target per Regime
| Strategia | Espansione | Rallentamento | Recessione |
|---|---|---|---|
| Long vol | 75% | 60% | 50% |
| Credit spread | 50% | 40% | 30% |
| Debit direzionale | 100% | 75% | 60% |
| Strutture avanzate (Jade, BWB) | 60% | 50% | 35% |

---

## 9. Pricing di Entrata per Titolo e Quota di Rischio

Il pricing non è solo una valutazione qualitativa del trade — determina direttamente quanta quota del rischio disponibile allocare su quel titolo specifico. Il flusso è sempre: valuta il prezzo → calcola il rischio per contratto → confronta con la quota disponibile → decidi se e quanti contratti aprire.

---

### Step 1 — Fair Value vs Mercato

Il primo filtro è l'edge teorico: stai pagando il giusto per quello che compri (o vendi)?

```python
edge = theoretical_value(σ=HV30) - market_price
# edge > 0    → stai comprando sotto fair value
# edge > 10%  → entry di qualità
# edge < 0    → stai pagando sopra fair value → riduci size o evita
```

Un edge negativo non blocca automaticamente l'entrata, ma riduce la quota di rischio allocabile su quel titolo. Un edge molto negativo (< −10%) è segnale di no entry indipendentemente dagli altri indicatori.

---

### Step 2 — IV/HV Ratio

Confronta la volatilità implicita (prezzo di mercato delle opzioni) con la volatilità storica realizzata (movimento reale del titolo):

| IV/HV Ratio | Interpretazione | Impatto sulla quota di rischio |
|---|---|---|
| < 0.80 | Eccellente — opzioni molto economiche | Quota piena |
| 0.80–0.90 | Buono | Quota piena |
| 0.90–1.00 | Neutro | Quota al 75% |
| 1.00–1.20 | Caro — IV sopra HV | Quota al 50% |
| > 1.20 | Molto caro | No entry su strategie long vol |

Il ratio > 1.0 è accettabile solo per strategie short vol (IC, Iron Butterfly, Jade Lizard) dove vendere IV sopra HV è esattamente il vantaggio cercato.

---

### Step 3 — Breakeven Raggiungibile

Verifica che il breakeven della struttura sia raggiungibile dal titolo in base alla sua volatilità storica:

```python
move_1sigma = spot * HV30 * sqrt(DTE/252)

# Per strategie long vol (Straddle, Strangle):
# BEP < 0.85 sigma  → OTTIMO — molto probabile
# BEP entro 1 sigma → raggiungibile
# BEP > 1.5 sigma   → EVITA — troppo lontano

# Per strategie short vol (IC, Iron Butterfly):
# Short strike > 1 sigma → OTTIMO — alta probabilità di profitto
# Short strike 0.85–1 sigma → accettabile
# Short strike < 0.85 sigma → ali troppo strette — rischio elevato
```

Se il BEP non è raggiungibile in condizioni normali del titolo, la quota allocabile si dimezza indipendentemente dagli altri indicatori.

---

### Step 4 — Bid/Ask per Titolo

Il bid/ask è il costo di esecuzione reale — si mangia direttamente il premio o il credito prima ancora che il trade inizi. Va calcolato correttamente e collegato alla quota di rischio disponibile.

#### Cos'è il Bid/Ask

Ogni opzione ha due prezzi:
- **Bid** — il prezzo a cui il market maker compra (tu vendi)
- **Ask** — il prezzo a cui il market maker vende (tu compri)
- **Mid** — la media dei due, il prezzo obiettivo di esecuzione

La differenza tra bid e ask è il costo pagato ad ogni apertura e chiusura. Su strutture multi-leg ogni gamba aggiunge il suo spread — l'effetto si moltiplica.

#### Il Problema sulle Strutture Multi-Leg

```
Iron Condor — 4 gambe:

Sell Put 184    bid 1.20 / ask 1.35  → spread 0.15
Buy  Put 179    bid 0.45 / ask 0.55  → spread 0.10
Sell Call 207   bid 0.90 / ask 1.05  → spread 0.15
Buy  Call 212   bid 0.30 / ask 0.40  → spread 0.10

Spread totale struttura: 0.50$ per contratto
Credito mid teorico:     1.25$
Bid/Ask sul netto:       0.50 / 1.25 = 40% — INACCETTABILE
```

Calcolare sempre il bid/ask sul **netto della struttura intera**, non sulla singola gamba.

#### Come Calcolarlo Correttamente

**Strategia a debito:**
```python
worst_case_debit = sum(ask for leg in long_legs) \
                 - sum(bid for leg in short_legs)
mid_debit        = sum(mid for leg in long_legs) \
                 - sum(mid for leg in short_legs)
bid_ask_pct      = (worst_case_debit - mid_debit) / mid_debit
```

**Strategia a credito:**
```python
worst_case_credit = sum(bid for leg in short_legs) \
                  - sum(ask for leg in long_legs)
mid_credit        = sum(mid for leg in short_legs) \
                  - sum(mid for leg in long_legs)
bid_ask_pct       = (mid_credit - worst_case_credit) / mid_credit
```

#### Soglie per Struttura e Impatto sulla Quota

Il bid/ask tollerabile varia in base al numero di gambe:

| Struttura | Gambe | Bid/Ask max | Impatto sulla quota |
|---|---|---|---|
| Single leg | 1 | 10% | Nessuna riduzione < 10% |
| Vertical Spread | 2 | 15% | Quota al 75% se 10–15% |
| Calendar / Diagonal | 2 | 15% | Quota al 75% se 10–15% |
| Broken Wing Butterfly | 3 | 20% | Quota al 75% se 15–20% |
| Jade Lizard / Reverse | 3 | 20% | Quota al 75% se 15–20% |
| Iron Condor / Iron Butterfly | 4 | 15% | Quota al 75% se 10–15% |

L'IC ha soglia più bassa delle strutture a 3 gambe perché il credito netto è già compresso — un bid/ask alto lo erode completamente.

**Soglia assoluta:** bid/ask > 15% sul netto per qualsiasi struttura → **no entry** indipendentemente dagli altri indicatori.

#### Liquidità del Titolo — Verifica Preliminare

Il bid/ask dipende dalla liquidità delle opzioni. Prima di analizzare qualsiasi setup verificare:

| Parametro | Ottimo | Accettabile | Evita |
|---|---|---|---|
| Open Interest per strike | > 1.000 | 500–1.000 | < 500 |
| Volume giornaliero opzioni | > 10.000 | 1.000–10.000 | < 1.000 |
| Bid/Ask assoluto per gamba | < 0.05$ | 0.05–0.15$ | > 0.20$ |

I titoli del framework (SPY, QQQ, IWM, GLD, TLT) soddisfano tutti questi parametri in condizioni normali.

#### Come Eseguire per Ridurre il Costo

**1. Ordine limite al mid** — sempre, mai ordini a mercato su opzioni.

**2. Tecnica del price improvement** — scala verso il mercato in incrementi di 0.05$:
```
Tentativo 1: mid esatto     → attendi 2 minuti
Tentativo 2: mid − 0.05$    → attendi 2 minuti
Tentativo 3: mid − 0.10$    → se non esegue, il trade non ha liquidità sufficiente
```

**3. Timing di esecuzione** — il bid/ask varia durante la sessione:

| Momento | Bid/Ask | Azione |
|---|---|---|
| Apertura (9:30–10:00) | Molto ampio | Evita |
| Metà mattina (10:00–12:00) | Stretto | Ideale per entrare |
| Early afternoon (12:00–14:00) | Medio | Accettabile |
| Ultima ora (15:00–16:00) | Si stringe | Buono per uscire |
| Pre/post market | Larghissimo | Mai operare |

#### Costo Reale di Esecuzione — Regola Finale

Prima di ogni trade calcola questo numero e aggiungilo al rischio effettivo:

```python
costo_esecuzione = bid_ask_pct * premio_o_credito_netto * 100

# Esempio IC con credito mid 1.25$ e bid/ask 20%:
costo_esecuzione = 0.20 * 1.25 * 100 = 25$ per contratto

# Se costo_esecuzione > 20% del profitto massimo atteso → no entry
# Il trade non ha senso economico indipendentemente dagli altri indicatori
```

---

### Step 5 — Score Pricing Composito per Titolo

I quattro fattori precedenti si sintetizzano in uno score da 0 a 100 specifico per il titolo analizzato:

```python
pricing_score = (
    w1 * edge_score          # peso 35 — edge teorico
  + w2 * iv_hv_score         # peso 30 — IV/HV ratio
  + w3 * bep_score           # peso 20 — raggiungibilità BEP
  + w4 * bidask_score        # peso 15 — costo di esecuzione
)
```

| Score | Valutazione | Quota di rischio sul titolo |
|---|---|---|
| > 75 | Eccellente | 100% della quota disponibile |
| 60–74 | Buono | 75% della quota disponibile |
| 45–59 | Sufficiente | 50% della quota disponibile |
| < 45 | Insufficiente | No entry su questo titolo |

---

### Collegamento Diretto con la Quota di Rischio

Il pricing score non è un giudizio astratto — riduce o conferma la quota di rischio allocabile su quel titolo specifico, che viene poi moltiplicata per i fattori di regime e Q_entry della Sezione 14.

**Esempio su due titoli in portafoglio contemporaneamente:**

```
Capitale totale: 10.000$
Rischio base per trade (3.5%): 350$

Titolo A — IWM Iron Condor
  Edge: +12%         → score edge: 85
  IV/HV: 1.33        → score iv/hv: 70 (short vol, accettabile)
  BEP: 1.1 sigma     → score bep: 75
  Bid/Ask: 6%        → score bidask: 90
  Pricing score: 78  → quota 100% → rischio allocabile: 350$
  Rischio per contratto: 375$ → 0 contratti (350$ < 375$)
  → Struttura troppo costosa per il budget. Ridurre ala a 4$
    oppure cercare credito superiore.

Titolo B — SPY Bull Call Spread
  Edge: +8%          → score edge: 72
  IV/HV: 0.88        → score iv/hv: 85
  BEP: 0.78 sigma    → score bep: 90
  Bid/Ask: 4%        → score bidask: 95
  Pricing score: 84  → quota 100% → rischio allocabile: 350$
  Rischio per contratto: 180$ → 1 contratto ✅
  Rischio effettivo: 180$ (1.8% del capitale)
```

La differenza tra i due titoli non è solo qualitativa — si traduce direttamente in contratti aperti e rischio allocato. IWM non entra non perché il setup sia cattivo, ma perché il rischio per contratto supera la quota disponibile con quella struttura.

---

### Verifica Finale Prima dell'Ordine

Prima di inviare l'ordine su ogni titolo, tre controlli rapidi:

```
☐ Pricing score > 45 sul titolo specifico
☐ Rischio per contratto ≤ quota di rischio aggiustata (regime × Q_entry × pricing)
☐ Bid/Ask verificato sul netto della struttura intera, non sulla singola gamba
☐ Rischio totale portafoglio dopo l'aggiunta ≤ 15% del capitale
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

## 12. [WIP] Portafoglio Rolling Cross-Asset

> **Sezione da completare quando saranno definiti i requisiti di capitale — vedere Sezione 14**

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

> **Punto aperto — da sviluppare quando saranno definiti i requisiti di capitale**

Temi da definire:
- Criteri quantitativi per la selezione dei titoli per ogni regime (correlazione, beta, liquidità opzioni)
- Logica di sizing tra posizioni diverse (Kelly, risk parity, volatility targeting)
- Come gestire la correlazione di portafoglio in tempo reale
- Ribilanciamento automatico al cambio di regime
- Numero ottimale di titoli per regime e massima esposizione per asset

---

## 14. Pricing e Sizing in Relazione al Rischio

### Il Vincolo Fondamentale

Il sizing non è una preferenza — è una regola di sopravvivenza del capitale. Ogni trade deve rispettare un limite non negoziabile indipendentemente dalla qualità del setup:

> **Rischio massimo per trade: 3–4% del capitale totale. Mai derogare.**

Con 3–4 posizioni aperte contemporaneamente l'esposizione totale al rischio si colloca tra il 9% e il 16% del portafoglio — una banda accettabile che lascia sempre capitale libero per opportunità e imprevisti.

---

### Passo 1 — Calcola il Rischio per Contratto

Il rischio per contratto dipende dalla struttura della strategia:

| Strategia | Formula rischio per contratto |
|---|---|
| Bull/Bear Spread | Premio pagato × 100 |
| Iron Condor / Iron Butterfly | (Larghezza ala − Credito) × 100 |
| Long Straddle / Strangle | Premio totale × 100 |
| Calendar / Diagonal | Premio netto × 100 |
| Jade Lizard / Reverse | (Strike put − Credito totale) × 100 |
| Broken Wing Butterfly | Rischio lato sfavorevole × 100 |

**Esempio Iron Condor con ala da 5$, credito 1.25$:**
```
Rischio per contratto = (5.00 - 1.25) × 100 = 375$
```

---

### Passo 2 — Applica il Moltiplicatore di Regime

Il regime macro riduce il rischio accettabile prima di calcolare i contratti:

| Regime | Moltiplicatore |
|---|---|
| Espansione | 100% |
| Rallentamento | 75% |
| Recessione | 50% |
| Stagflazione | 50% |
| Crisi | 0% — nessuna nuova posizione |

---

### Passo 3 — Calcola i Contratti

```python
def calcola_contratti(capitale, rischio_pct, regime_mult, q_entry,
                      pricing_score, rischio_per_contratto):

    # Rischio base (3.5% come punto medio del range 3–4%)
    rischio_base = capitale * rischio_pct

    # Moltiplicatore Q_entry
    if q_entry > 75:
        q_mult = 1.0
    elif q_entry >= 60:
        q_mult = 0.75
    else:
        return 0  # No entry

    # Moltiplicatore Pricing score
    if pricing_score > 75:
        p_mult = 1.0
    elif pricing_score >= 60:
        p_mult = 0.75
    elif pricing_score >= 45:
        p_mult = 0.50
    else:
        return 0  # No entry

    # Rischio aggiustato finale
    rischio_finale = rischio_base * regime_mult * q_mult * p_mult

    # Contratti (mai frazioni — arrotonda sempre al ribasso)
    return max(floor(rischio_finale / rischio_per_contratto), 0)
```

**Esempio completo:**
```
Capitale:            10.000$
Rischio base 3.5%:     350$
Regime Rallentamento:  × 0.75 → 262$
Q_entry 68:            × 0.75 → 196$
Pricing score 71:      × 0.75 → 147$

Rischio per contratto IC: 375$
Contratti: floor(147 / 375) = 0 → NO ENTRY

→ Il framework segnala che la strategia non è eseguibile
  in questo contesto. Scegliere una struttura con rischio
  per contratto inferiore o attendere un regime migliore.
```

---

### Gestione dell'Esposizione Totale di Portafoglio

Con 3–4 posizioni aperte in parallelo il rischio si accumula. Tre limiti operano simultaneamente:

**Limite 1 — Rischio per trade: 3–4% del capitale**
Ogni singola posizione non può perdere più del 4% del capitale totale.

**Limite 2 — Rischio totale portafoglio: massimo 15%**
La somma del rischio massimo di tutte le posizioni aperte non supera il 15% del capitale.

```
Posizione 1 — IC IWM:         rischio 375$   (3.75%)
Posizione 2 — Bull Spread SPY: rischio 200$   (2.00%)
Posizione 3 — Calendar QQQ:    rischio 150$   (1.50%)
─────────────────────────────────────────────────────
Totale rischio aperto:          725$   (7.25%) ✅
Spazio residuo per 4a posizione: 775$  (7.75%)
```

**Limite 3 — Correlazione: un solo trade per asset**
Due posizioni sullo stesso sottostante nello stesso mese non sono due trade indipendenti — sono la stessa scommessa con doppia esposizione. Il framework ammette un solo trade per asset e diversifica tra sottostanti decorrelati.

---

### Margine Bloccato

Le strategie a credito incassano denaro subito ma immobilizzano margine. Tenerlo sempre in conto nella pianificazione:

| Strategia | Margine bloccato per contratto |
|---|---|
| Iron Condor (5$ ala) | (Larghezza − Credito) × 100 |
| Bull Put / Bear Call Spread | (Larghezza − Credito) × 100 |
| Long Straddle / Strangle | Solo premio — nessun margine aggiuntivo |
| Calendar / Diagonal | Premio netto — nessun margine aggiuntivo |

Con 3 posizioni a credito aperte il margine bloccato può rappresentare il 10–12% del capitale — quella quota non è disponibile per nuove opportunità. Monitorarlo come parte della gestione del portafoglio.

---

### Quando il Calcolo Restituisce Zero Contratti

Se il calcolo porta a 0 contratti su tutte le strategie compatibili con il regime corrente, le opzioni sono due sole:

**1. Aspetta** — il regime cambierà, la IV si muoverà, arriverà un setup con rischio per contratto più contenuto. Non esistono trade obbligatori.

**2. Scala la struttura** — usa ali più strette (es. 3$ invece di 5$) per ridurre il rischio per contratto. Verificare però che il bid/ask rimanga sotto il 15% del mid e che il credito o il premio abbiano ancora senso economico dopo le commissioni.

Non esiste una terza opzione. Forzare un trade fuori dai parametri di rischio per evitare di "stare fermi" è la causa principale delle perdite strutturali nei portafogli in fase di costruzione.

---

## Changelog

| Versione | Modifica |
|---|---|
| v4 | Sezione 9 Step 4 espansa — guida completa al bid/ask con calcolo per struttura, soglie per numero di gambe, liquidità del titolo, tecniche di esecuzione e costo reale |
| v4 | Sezione 9 riscritta — pricing per titolo collegato direttamente alla quota di rischio del capitale |
| v4 | Aggiunta Sezione 14 — Pricing e Sizing in relazione al rischio |
| v4 | Sezioni 12 e 13 marcate WIP — da completare con requisiti di capitale del portafoglio rotazionale |
| v3 | Rimossi Short Straddle e Short Strangle — incompatibili con il principio fondante del rischio definito |
| v3 | Aggiunto principio fondante esplicito in apertura documento |
| v3 | Aggiunte Famiglia 5: Calendar Spread, Jade Lizard, Reverse Jade Lizard, Broken Wing Butterfly, Diagonal Spread |
| v3 | Aggiornata matrice strategia per regime con le nuove strategie |
| v3 | Aggiornata tabella riepilogativa con tutte le strategie |
| v3 | Aggiornati stop loss e profit target per le nuove strategie |
| v3 | Aggiornata mappa quadranti Zona A/B/C/D con nuove strategie |
| v2 | Versione precedente |

---

*Documento generato dalla sessione di design — aggiornato progressivamente*
