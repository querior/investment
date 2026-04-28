# Learning Path — Options Engine con Python, ML e DL

> Documento di tracciamento progressivo — aggiornato sessione per sessione.
> Caso concreto di riferimento: **Options Engine Framework v2**

---

## Struttura generale

Il percorso è diviso in due blocchi sequenziali:

- **Blocco A — Foundation (Moduli 1–6):** pipeline dati, pricing, strategy selector, backtest, API, visualizzazione
- **Blocco B — ML/DL Layer (Moduli ML-A, ML-B, ML-C):** classificazione regime, forecasting volatilità, sizing con RL

Ogni modulo produce un componente reale che si integra nel successivo. La codebase è cumulativa.

---

## Blocco A — Foundation

### Modulo 1 — Data pipeline
**Obiettivo:** costruire la base dati del framework — serie storiche, calcolo IV Rank, HV, squeeze indicator.

**Librerie:** `pandas` · `numpy` · `yfinance`

**Concetti chiave:**
- Strutture dati pandas: Series, DataFrame, MultiIndex per dati options
- Operazioni vettorizzate numpy vs loop Python (performance su serie lunghe)
- Rolling windows: `rolling()`, `ewm()`, percentile rank su finestra mobile
- Download dati OHLCV con yfinance, gestione dei gap di mercato
- Calcolo IV Rank e IV Percentile come descritto nella Section 5 del framework

**Output del modulo:** `data/loader.py` + `data/features.py` con funzioni `compute_iv_rank()`, `compute_hv()`, `compute_squeeze()`

**Riferimento framework:** Section 4 (stack tecnologico), Section 5 (segnali primari)

**Stato:** ⬜ da iniziare

---

### Modulo 2 — Option pricing
**Obiettivo:** calcolare il fair value teorico, le greche e l'edge di ogni potenziale trade.

**Librerie:** `mibian` · `py_vollib` · `numpy`

**Concetti chiave:**
- Black-Scholes: intuizione del modello, parametri (S, K, T, r, σ)
- Greche: Delta (esposizione direzionale), Vega (esposizione IV), Theta (decadimento temporale), Gamma (accelerazione Delta)
- Differenza tra IV implicita (dal mercato) e HV storica (dai prezzi)
- Edge teorico: `theoretical_value(σ=HV30) - market_price`
- IV/HV ratio come filtro qualità (tabella Section 9)
- Calcolo BEP e verifica raggiungibilità in sigma (Section 9)
- Bid/ask spread come costo nascosto su strutture multi-leg

**Output del modulo:** `engine/pricing.py` con funzioni `greeks()`, `compute_edge()`, `pricing_score()`

**Riferimento framework:** Section 2 (greche per strategia), Section 9 (pricing di entrata)

**Stato:** ⬜ da iniziare

---

### Modulo 3 — Strategy selector
**Obiettivo:** implementare la logica di selezione strategia e il Q_entry score composito.

**Librerie:** `numpy` · `scipy.optimize` · `pandas`

**Concetti chiave:**
- Classificazione regime: Zone A/B/C/D (ADX × IV), 5 regimi macro
- Score composito Q_entry con pesi w1–w6 (Section 5)
- `scipy.optimize` per calibrare i pesi su dati storici
- Matrice strategia per regime (Section 7): quale strategia in quale contesto
- Soglie operative: > 75 full size / 60–74 size ridotta / < 60 no entry

**Output del modulo:** `engine/strategy.py` con `classify_regime()`, `compute_q_entry()`, `select_strategy()`

**Riferimento framework:** Section 5 (segnali ingresso), Section 6 (regime macro), Section 7 (matrice strategia)

**Stato:** ⬜ da iniziare

---

### Modulo 4 — Backtest engine
**Obiettivo:** testare le strategie su dati storici con ottimizzazione bayesiana dei parametri.

**Librerie:** `vectorbt` · `optuna` · `quantstats`

**Concetti chiave:**
- Backtest vettorizzato con vectorbt vs event-driven con backtrader: trade-off velocità/flessibilità
- Walk-forward validation: evitare overfitting su parametri ottimizzati
- Optuna: Bayesian optimization con TPE Sampler, pruning, ~500 trial invece di 86.000 (grid search)
- Stop loss e profit target per regime (Section 8)
- Report con quantstats: Sharpe, Sortino, max drawdown, calmar ratio
- Adjustment e roll Iron Condor (Section 11)

**Output del modulo:** `engine/backtest.py` + `optimizer/objective.py` + `analysis/report.py`

**Riferimento framework:** Section 4 (architettura), Section 8 (uscite), Section 11 (adjustment IC)

**Stato:** ⬜ da iniziare

---

### Modulo 5 — API layer
**Obiettivo:** esporre il framework come servizio con endpoint REST e pipeline asincrona.

**Librerie:** `FastAPI` · `Pydantic` · `asyncio`

**Concetti chiave:**
- Pydantic: validazione dei dati in ingresso con modelli tipizzati (regime, IV rank, DTE, strategia)
- FastAPI: routing, dependency injection, gestione errori
- `async`/`await`: fetch parallelo di dati per più ticker senza bloccare il thread
- WebSocket per streaming delle greche live
- Poetry: gestione dipendenze con `pyproject.toml`, lock file, virtual environment
- pyenv: gestione versioni Python per isolamento del progetto

**Output del modulo:** `api/main.py` + `api/models.py` + `api/routes/analyze.py`

**Riferimento framework:** struttura modulare Section 4

**Stato:** ⬜ da iniziare

---

### Modulo 6 — Visualization & packaging
**Obiettivo:** dashboard interattiva con payoff diagram e packaging finale del progetto.

**Librerie:** `plotly` · `Poetry` · `pyenv`

**Concetti chiave:**
- Plotly: payoff diagram interattivi per ogni strategia (bull call spread, iron condor, straddle)
- P&L per regime: confronto visivo dei risultati per contesto macro
- Grafici greche in funzione del prezzo e del tempo residuo (DTE)
- `pyproject.toml`: struttura completa del pacchetto, dipendenze opzionali, entry points
- Dockerfile di base per deployment

**Output del modulo:** `analysis/charts.py` + `pyproject.toml` completo + `README.md`

**Riferimento framework:** Section 10 (casi reali IWM)

**Stato:** ⬜ da iniziare

---

## Blocco B — ML/DL Layer

> I moduli ML si innestano sul Blocco A: ogni modello prende in input le feature costruite nei moduli 1–3 e restituisce output che migliorano la qualità delle decisioni del framework.

---

### Modulo ML-A — Regime classifier
**Obiettivo:** sostituire la classificazione binaria del regime (regole fisse su soglie) con una probabilità continua appresa dai dati.

**Librerie:** `scikit-learn` · `XGBoost` / `LightGBM` · `SHAP`

**Concetti chiave — ML:**
- Classificazione multiclasse: 5 regimi come label target
- Feature tabellari su dati macro: `PMI_delta`, `yield_curve_spread`, `VIX_30d_change`, `HY_spread_percentile`, `pct_stocks_above_ma200`
- Train/validation/test split su serie temporali: **no random shuffle** (look-ahead bias)
- `Pipeline` e `ColumnTransformer` scikit-learn per preprocessing riproducibile
- `RandomForestClassifier` come baseline: feature importance, no overfitting implicito
- `XGBoost`/`LightGBM`: gradient boosting, hyperparameter tuning con Optuna
- `cross_val_score` con `TimeSeriesSplit`
- SHAP values: spiegabilità del modello — quali feature guidano ogni previsione

**Concetti chiave — feature engineering su serie temporali:**
- Lag features: valore della feature ai timestep t-1, t-5, t-20
- Rolling statistics: media, std, z-score su finestre multiple
- Non-stazionarietà: lavorare su differenze/variazioni invece di livelli assoluti
- Cross-asset correlations come feature di regime

**Output del modello:** `P(regime)` — vettore di probabilità per ognuno dei 5 regimi. Alimenta il sizing dinamico: size proporzionale a `P(regime_favorevole)` invece di un moltiplicatore fisso.

**Output del modulo:** `ml/regime_classifier.py` + `ml/features_macro.py`

**Riferimento framework:** Section 6 (classificazione regime), Section 7 (matrice strategia × regime)

**Stato:** ⬜ da iniziare

---

### Modulo ML-B — Volatility forecaster
**Obiettivo:** prevedere l'IV attesa nei prossimi 5–10 giorni per migliorare il calcolo dell'edge.

**Librerie:** `PyTorch` · `TensorFlow/Keras` (confronto) · `numpy`

**Concetti chiave — DL e serie temporali:**
- Perché i modelli standard falliscono sulle serie finanziarie: non-stazionarietà, fat tails, regime-switching
- Finestre scorrevoli (`sliding windows`) per costruire sequenze input/target
- LSTM: cella di memoria, hidden state, forget gate — intuizione e implementazione in PyTorch
- `nn.Module`: struttura base di un modello PyTorch
- Training loop da zero: forward pass, loss, `optimizer.step()`, gradient clipping
- `DataLoader` e `Dataset`: batching efficiente di sequenze temporali
- Early stopping e learning rate scheduling
- Confronto con Keras: stesso modello in 10 righe vs 40 — cosa si guadagna e perde

**Concetti chiave — feature engineering per vol forecasting:**
- IV surface features: skew (slope strike), term structure (IV 30d / IV 90d)
- Realized vs implied vol spread come predittore di mean-reversion
- Log-returns e loro proprietà statistiche
- Normalizzazione per sequenza (non globale) per evitare data leakage

**Output del modello:** `IV_forecast_5d` — stima scalare dell'IV attesa. Sostituisce l'uso di HV30 come proxy nel calcolo dell'edge (Section 9): `edge = theoretical_value(σ=IV_forecast) - market_price`.

**Output del modulo:** `ml/vol_forecaster.py` + `ml/features_options.py`

**Riferimento framework:** Section 9 (pricing di entrata, IV/HV ratio)

**Stato:** ⬜ da iniziare

---

### Modulo ML-C — Sizing optimizer (RL)
**Obiettivo:** imparare una policy di sizing ottimale che si adatta dinamicamente al regime e al rischio di portafoglio.

**Librerie:** `PyTorch` · `Stable-Baselines3` · `gymnasium`

**Concetti chiave — Reinforcement Learning:**
- MDP: stato, azione, reward, transizione — come si mappa sul problema del sizing
- Stato osservabile: `[P(regime), IV_rank, Q_entry, current_drawdown, portfolio_delta, days_in_trade]`
- Azione: size come percentuale del capitale (continua) o bucket discreto (0%, 25%, 50%, 75%, 100%)
- Reward: Sharpe ratio rolling aggiustato per regime — penalizza rischio in Recessione, premia rendimento in Espansione
- PPO (Proximal Policy Optimization): algoritmo stabile per spazi d'azione continui
- `gymnasium`: definire un environment custom che wrappa il backtest engine
- Stable-Baselines3: training di PPO senza implementare l'algoritmo da zero
- Curriculum learning: allenare prima su regime Espansione, poi introdurre gradualmente Recessione e Crisi

**Concetti chiave — insidie specifiche del RL finanziario:**
- Overfitting alla storia: il modello impara il passato, non il futuro
- Non-stazionarietà dell'environment: i mercati cambiano strutturalmente
- Reward shaping: una reward mal definita produce comportamenti degeneri
- Evaluation out-of-sample su periodi disgiunti di training

**Output del modello:** policy di sizing `π(s) → size%` — sostituisce i moltiplicatori fissi della Section 7.

**Output del modulo:** `ml/rl_sizer.py` + `ml/envs/options_env.py`

**Riferimento framework:** Section 7 (sizing per regime), Section 12 (portafoglio rolling cross-asset)

**Stato:** ⬜ da iniziare

---

## Tracciamento sessioni

| Data | Modulo | Argomenti trattati | Note |
|------|--------|-------------------|------|
| — | — | — | — |

---

## Dipendenze e ambiente

```toml
# pyproject.toml — dipendenze cumulative

[tool.poetry.dependencies]
python = "^3.11"

# Blocco A
pandas = "^2.2"
numpy = "^1.26"
yfinance = "^0.2"
mibian = "*"
py_vollib = "*"
pandas-ta = "*"
vectorbt = "*"
optuna = "^3.6"
quantstats = "*"
fastapi = "^0.111"
uvicorn = "^0.30"
pydantic = "^2.7"
plotly = "^5.22"

# Blocco B
scikit-learn = "^1.5"
xgboost = "^2.0"
lightgbm = "^4.3"
shap = "^0.45"
torch = "^2.3"
tensorflow = "^2.16"
stable-baselines3 = "^2.3"
gymnasium = "^0.29"
```

```bash
# Setup ambiente
pyenv install 3.11.9
pyenv local 3.11.9
poetry install
```

---

## Struttura codebase target

```
options-engine/
├── data/
│   ├── loader.py          # Modulo 1
│   └── features.py        # Modulo 1 + ML-A/B
├── engine/
│   ├── pricing.py         # Modulo 2
│   ├── strategy.py        # Modulo 3
│   └── backtest.py        # Modulo 4
├── optimizer/
│   └── objective.py       # Modulo 4
├── ml/
│   ├── regime_classifier.py   # ML-A
│   ├── vol_forecaster.py      # ML-B
│   ├── rl_sizer.py            # ML-C
│   ├── features_macro.py      # ML-A
│   ├── features_options.py    # ML-B
│   └── envs/
│       └── options_env.py     # ML-C
├── api/
│   ├── main.py            # Modulo 5
│   ├── models.py          # Modulo 5
│   └── routes/
│       └── analyze.py     # Modulo 5
├── analysis/
│   ├── report.py          # Modulo 4
│   └── charts.py          # Modulo 6
├── pyproject.toml         # Modulo 5-6
└── README.md              # Modulo 6
```

---

## Legenda stati

| Simbolo | Significato |
|---------|-------------|
| ⬜ | Da iniziare |
| 🔄 | In corso |
| ✅ | Completato |
| ⏸ | In pausa / bloccato |

---

*Documento di lavoro — aggiornare lo stato e la tabella sessioni ad ogni avanzamento.*
