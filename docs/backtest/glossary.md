# 📘 Glossary — Trading & Backtesting

---

## Payoff

Valore finale di una posizione in funzione del prezzo del sottostante alla scadenza.

Rappresenta la relazione tra prezzo del sottostante e profitto/perdita.

Esempio (call):

$$
\text{Payoff} = \max(S_T - K, 0)
$$

---

## Convexity

Proprietà di una funzione di avere curvatura verso l’alto (forma ∪).

In ambito trading indica strategie che:

* beneficiano di movimenti ampi del mercato
* hanno perdite limitate e guadagni potenzialmente elevati

Formalmente:

$$
\frac{d^2 f}{dx^2} > 0
$$

---

## Concavity

Proprietà di una funzione di avere curvatura verso il basso (forma ∩).

In ambito trading indica strategie che:

* generano guadagni limitati e frequenti
* sono esposte a perdite elevate in caso di movimenti forti

Formalmente:

$$
\frac{d^2 f}{dx^2} < 0
$$

---

## Sharpe Ratio

Misura il rendimento corretto per il rischio.

Indica quanto rendimento si ottiene per unità di volatilità.

$$
\text{Sharpe} = \frac{E[R - R_f]}{\sigma(R)}
$$

Dove:

* $R$ = rendimento del portafoglio
* $R_f$ = tasso risk-free
* $\sigma$ = deviazione standard dei rendimenti

---

## CAGR (Compound Annual Growth Rate)

Tasso di crescita annuale composto di un investimento.

$$
\text{CAGR} = \left( \frac{V_f}{V_i} \right)^{\frac{1}{n}} - 1
$$

Dove:

* $V_f$ = valore finale
* $V_i$ = valore iniziale
* $n$ = numero di anni

---

## Drawdown

Riduzione percentuale dal massimo storico al minimo successivo.

$$
\text{Drawdown}*t = \frac{V_t - \max(V*{0:t})}{\max(V_{0:t})}
$$

Il massimo drawdown è il valore minimo della serie dei drawdown.

---

## Implied Volatility

## Implied Volatility (IV)

è la volatilità **attesa dal mercato** incorporata nel prezzo delle opzioni.

---

### Definizione

È il valore di volatilità che, inserito in un modello di pricing (es. Black-Scholes), restituisce il prezzo osservato dell’opzione.

---

### Interpretazione

- non è osservata direttamente
- è **implicita nei prezzi delle opzioni**
- rappresenta le aspettative future di variabilità del mercato

---

### Intuizione

- IV alta → mercato si aspetta movimenti ampi  
- IV bassa → mercato si aspetta stabilità  

---

### Differenza con Realized Volatility

| Tipo | Cosa misura | Fonte |
|------|------------|------|
| **IV** | volatilità attesa | mercato opzioni |
| **RV** | volatilità passata | prezzi |

---

### Utilizzo nel trading

- IV > RV → opzioni “care” → strategie short volatility  
- IV < RV → opzioni “a buon prezzo” → strategie long volatility  

---

### TL;DR

Implied volatility = **aspettativa di volatilità futura derivata dai prezzi delle opzioni**


---

### Realized Volatility (RV)

Realized volatility (RV) = volatilità effettivamente osservata nei prezzi passati, quanto il prezzo si è mosso. È la deviazione standard dei rendimenti su una finestra temporale.

$$
RV = \sqrt{252} \cdot \operatorname{std}(r_{t-n:t})
$$

dove:
- \( r \) = rendimenti (log returns)
- \( n \) = numero di periodi (es. 20 giorni)
- \( \sqrt{252} \) = annualizzazione

implementazione in python:

```python
log_ret = np.log(df["close"] / df["close"].shift(1))
rv_20 = log_ret.rolling(20).std() * np.sqrt(252)
```

---

## Gamma

Misura la variazione del delta rispetto al prezzo del sottostante.

$$
\Gamma = \frac{\partial^2 V}{\partial S^2}
$$

Indica la curvatura della posizione.

---

## Long Gamma

Posizione con gamma positivo.

Caratteristiche:

* comportamento convesso
* beneficia di movimenti ampi del mercato
* perdite limitate

---

## Short Gamma

Posizione con gamma negativo.

Caratteristiche:

* comportamento concavo
* guadagni limitati e frequenti
* rischio di perdite elevate in movimenti forti

---

## Theta Decay

Perdita di valore delle opzioni dovuta al passare del tempo.

$$
\Theta = \frac{\partial V}{\partial t}
$$

* long option → theta negativo (perdi valore)
* short option → theta positivo (guadagni dal tempo)

---

## Vega

Sensibilità del prezzo dell’opzione alla variazione della volatilità implicita.

$$
\text{Vega} = \frac{\partial V}{\partial \sigma}
$$

* vega positivo → benefici da aumento IV
* vega negativo → soffri aumento IV


---

## Short Volatility

Strategia che beneficia di una diminuzione o stabilità della volatilità implicita.

Caratteristiche:

* guadagni graduali
* rischio elevato in caso di aumento improvviso della volatilità

Esempi:

* bull put spread
* bear call spread

---

## Long Volatility

Strategia che beneficia di un aumento della volatilità implicita.

Caratteristiche:

* perdita costante nel tempo (theta)
* guadagni elevati in caso di movimenti forti

Esempi:

* long straddle
* long call
* long put

---

## RSI — Relative Strength Index

Oscillatore di momentum che misura la velocità e l'ampiezza dei movimenti di
prezzo su una finestra mobile (tipicamente 14 periodi). Scala da 0 a 100:
valori > 70 indicano ipercomprato, < 30 ipervenduto. Nel framework è usato
come filtro di neutralità direzionale — l'ingresso è preferito con RSI in
zona [40, 60], segnale che il titolo non è in trend esteso in nessuna direzione.

$$RSI = 100 - \frac{100}{1 + RS}$$

dove $RS = \dfrac{\text{media guadagni su } n \text{ periodi}}{\text{media perdite su } n \text{ periodi}}$

---

## MACD — Moving Average Convergence Divergence

Indicatore di trend e momentum costruito come differenza tra due medie mobili
esponenziali (EMA 12 e EMA 26), a cui si sovrappone una linea segnale
(EMA 9 del MACD stesso). Quando il MACD è piatto e vicino allo zero indica
assenza di impulso direzionale — condizione ricercata dal framework per i
setup a volatilità (Straddle, Strangle, Iron Condor), dove un trend in atto
aumenta il rischio di rottura della struttura.

$$MACD = EMA_{12}(P) - EMA_{26}(P)$$

$$\text{Segnale} = EMA_9(MACD)$$

$$\text{Istogramma} = MACD - \text{Segnale}$$

---

## ADX — Average Directional Index

Misura la forza del trend in corso indipendentemente dalla direzione
(rialzista o ribassista). Scala da 0 a 100: sotto 20 mercato laterale,
sopra 25 trend direzionale strutturato, sopra 30 trend forte. Nel framework
è uno degli assi della classificazione a quadranti (Zona A/B vs Zona C/D):
ADX < 25 definisce i regimi laterali dove sono indicati Iron Condor e
strutture short vol; ADX > 25 orienta verso spread direzionali.

$$+DM = H_t - H_{t-1} \quad \text{se positivo, altrimenti } 0$$
$$-DM = L_{t-1} - L_t \quad \text{se positivo, altrimenti } 0$$

$$TR = \max(H_t - L_t,\ |H_t - C_{t-1}|,\ |L_t - C_{t-1}|)$$

$$+DI = 100 \cdot \frac{EMA_{14}(+DM)}{EMA_{14}(TR)} \qquad
-DI = 100 \cdot \frac{EMA_{14}(-DM)}{EMA_{14}(TR)}$$

$$ADX = EMA_{14}\!\left(100 \cdot \frac{|{+DI} - {-DI}|}{+DI + -DI}\right)$$

---

## IV Rank

Misura dove si colloca l'IV attuale rispetto al suo range storico degli
ultimi 52 settimane. Non è influenzata dalla distribuzione delle osservazioni
— dipende solo dal massimo e dal minimo del periodo.

$$IV\_Rank = \frac{IV_{attuale} - IV_{min_{52w}}}{IV_{max_{52w}} - IV_{min_{52w}}} \times 100$$

| IV Rank | Interpretazione | Approccio |
|---|---|---|
| < 30% | Opzioni economiche | Comprare volatilità (long premium) |
| 30–50% | Neutro | Spread direzionali bilanciati |
| > 50% | Opzioni care | Vendere volatilità (short premium) |

---

## IV Percentile

Percentuale di giorni nell'ultimo anno in cui l'IV era inferiore al valore
attuale. A differenza dell'IV Rank non è distorta da picchi estremi: se la
IV ha toccato un massimo anomalo una sola volta, l'IV Rank può risultare
basso anche con IV oggettivamente alta, mentre l'IV Percentile riflette la
distribuzione reale delle osservazioni.

$$IV\_Percentile = \frac{\text{numero di giorni con } IV < IV_{attuale}}
{\text{totale giorni nel periodo}} \times 100$$

Nel framework è usato in coppia con l'IV Rank come conferma — l'ingresso
long vol richiede entrambi sotto soglia:

$$IV\_Rank < 30\% \quad \cap \quad IV\_Percentile < 25\%$$

## DTE — Days to Expiration

Numero di giorni di calendario che mancano alla scadenza del contratto
opzione. È un parametro critico perché governa il decadimento temporale
(Theta) e il rischio Gamma: con DTE alto il decadimento è lento ma la
struttura è più robusta ai movimenti di prezzo; con DTE basso il decadimento
accelera ma il Gamma aumenta, rendendo la posizione più sensibile a ogni
variazione del sottostante.

Il decadimento temporale non è lineare — accelera in modo approssimato
alla radice del tempo residuo:

$$\text{decadimento giornaliero} \propto \frac{1}{\sqrt{DTE}}$$

---

## TTM Squeeze

Indicatore composito che segnala la compressione della volatilità — il
momento in cui le Bande di Bollinger si restringono all'interno del Canale
di Keltner. Combina due misure di volatilità su scale diverse per
identificare i periodi di lateralità estrema che precedono storicamente
i movimenti esplosivi di prezzo.

**Bande di Bollinger** — volatilità statistica basata sulla deviazione
standard dei prezzi:

$$BB_{upper} = SMA_{20} + 2\sigma_{20} \qquad BB_{lower} = SMA_{20} - 2\sigma_{20}$$

**Canale di Keltner** — volatilità di range basata su ATR:

$$KC_{upper} = EMA_{20} + 1.5 \cdot ATR_{20} \qquad KC_{lower} = EMA_{20} - 1.5 \cdot ATR_{20}$$

Lo squeeze è **attivo** quando le Bande di Bollinger sono interamente
contenute nel Canale di Keltner:

$$BB_{upper} < KC_{upper} \quad \cap \quad BB_{lower} > KC_{lower}$$

Lo squeeze si **rilascia** quando le BB escono dal KC — segnale che la
compressione sta terminando e un movimento direzionale è imminente.
Il TTM Squeeze non indica la direzione del breakout, solo che la
compressione è in atto.

