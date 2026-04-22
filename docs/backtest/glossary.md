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


