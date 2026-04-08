# Backtest Options

## Obiettivo

Costruire un motore di backtest per strategie opzionali su ETF/indici con:

* pricing teorico tramite Black-Scholes
* greche aggregate
* gestione di spread e strutture a rischio definito
* persistenza di posizioni, snapshot e performance
* possibile integrazione futura con segnali macro

---

## Architettura concettuale

Separazione in tre livelli:

1. **Domain / runtime model**

   * `OptionLeg`
   * `Position`
   * `PortfolioSnapshot`
   * `Portfolio`

2. **Persistence model**

   * `BacktestRun`
   * `BacktestPosition`
   * `BacktestPositionSnapshot`
   * `BacktestPortfolioPerformance`

3. **Backtest engine**

   * ciclo giornaliero
   * update prezzi e greche
   * close logic
   * entry logic
   * salvataggio snapshot

---

## Flusso del ciclo di backtest

Per ogni giorno:

1. Legge `date`, `close`, `iv`
2. Aggiorna le posizioni aperte (`S`, `IV`, `T`)
3. Ricalcola prezzo posizione e greche
4. Salva snapshot posizione
5. Valuta eventuale chiusura
6. Apre nuove posizioni se le condizioni lo permettono
7. Salva snapshot portfolio

Il segnale macro, quando verrà integrato, va usato **solo in apertura** come contesto di regime.

---

## Pricing e greche

Per il pricing è stata definita una struttura `OptionState` con:

* `option_type`
* `S`
* `K`
* `T`
* `r`
* `sigma`

Le greche usate nel motore:

* Delta
* Gamma
* Theta giornaliera
* Vega per punto IV

### Formula locale utile

```python
def option_price_local_approx(
    current_price: float,
    dS: float,
    d_iv_points: float,
    dt_days: float,
    greeks: Greeks,
) -> float:
    return (
        current_price
        + greeks.delta * dS
        + 0.5 * greeks.gamma * (dS ** 2)
        + greeks.vega_per_iv_point * d_iv_points
        + greeks.theta_daily * dt_days
    )
```

Questa formula è utile per simulazioni rapide, non per pricing definitivo.

---

## Runtime model

### `OptionLeg`

Rappresenta una gamba della posizione:

* segno (`+1` long, `-1` short)
* quantità
* stato dell’opzione

### `Position`

Rappresenta una struttura composta da più gambe:

* nome posizione
* gambe
* valore iniziale
* stato open/closed
* metodi per prezzo, pnl e greche aggregate

### `Portfolio`

Tiene traccia di:

* cash
* posizioni aperte
* equity
* greche aggregate
* storico snapshot

---

## Close logic

È stata definita una prima logica semplice di uscita:

* chiusura se profitto >= 50% del credito iniziale
* chiusura a 21 DTE

### Funzione significativa

```python
def should_close_position(position: Position) -> bool:
    current_value = position.price()
    pnl = current_value - position.initial_value

    if position.initial_value < 0 and pnl >= abs(position.initial_value) * 0.5:
        return True

    min_t = min(leg.state.T for leg in position.legs)
    if min_t <= 21 / 365.0:
        return True

    return False
```

---

## Entry logic iniziale

Per la prima versione il motore apre una posizione ogni `entry_every_n_days`.

La prima struttura usata è un **bull put spread** con:

* DTE 45
* strike short ~95% del sottostante
* strike long ~92% del sottostante

Questa logica è provvisoria e verrà poi sostituita con una policy guidata dal regime macro e dal regime IV.

---

## Esecuzione del backtest

### Struttura della funzione

La funzione `run_eod_backtest(...)`:

* riceve `db`, `run`, `df`
* itera sui dati giornalieri
* aggiorna le posizioni runtime
* salva dati su DB tramite i nuovi model

### Pattern rilevante sul loop

```python
for i, (_, row) in enumerate(df.iterrows()):
    snapshot_date = row["date"].date() if hasattr(row["date"], "date") else row["date"]
    S = float(row["close"])
    iv = float(row["iv"])
```

`enumerate(...)` è stato introdotto per evitare problemi con `%` quando l’indice del DataFrame non è intero.

---

## Simulazione della IV

È stato definito un approccio semplice ma realistico per simulare la volatilità implicita partendo dai prezzi:

1. rendimenti logaritmici
2. rolling std (es. 20 giorni)
3. annualizzazione
4. moltiplicatore (`k`, es. 1.15)
5. clamp min/max
6. eventuale boost downside

### Formula concettuale

[
IV_t = clamp\Big(1.15 \cdot \sqrt{252} \cdot std(r_{t-19:t}) + \alpha \cdot \max(0, -r_t)\Big)
]

Questa IV è unica per il giorno e non rappresenta ancora una surface per strike/scadenza.

---

## Data acquisition da DB

I dati di mercato vengono letti da database e trasformati in DataFrame.

### Pattern corretto

```python
rows = [
    {
        "symbol": x.symbol,
        "date": x.date,
        "close": x.close,
    }
    for x in data
]

df = pd.DataFrame(rows)
```

Questo evita l’errore di shape che si verifica passando direttamente oggetti ORM a `pd.DataFrame(..., columns=[...])`.

---

## Gestione errori

Il pattern adottato per l’esecuzione del backtest è:

* `try/except`
* `rollback()` in caso di errore
* salvataggio di `run.error_message`
* rilancio dell’eccezione

### Pattern sintetico

```python
try:
    # business logic
    db.commit()
except Exception as e:
    db.rollback()
    run.error_message = str(e)
    db.commit()
    raise
```

---

## Persistenza: model DB introdotti

### `BacktestPosition`

Testata della posizione/trade:

* `run_id`
* `position_type`
* `status`
* `opened_at`
* `closed_at`
* `entry_underlying`
* `entry_iv`
* `entry_macro_regime`
* `initial_value`
* `close_value`
* `realized_pnl`

### `BacktestPositionSnapshot`

Snapshot giornaliero della singola posizione:

* `snapshot_date`
* `underlying_price`
* `iv`
* `position_price`
* `position_pnl`
* `position_delta`
* `position_gamma`
* `position_theta`
* `position_vega`
* `min_dte`
* `is_open`

### `BacktestPortfolioPerformance`

Snapshot giornaliero del portafoglio:

* `cash`
* `positions_value`
* `total_equity`
* `realized_pnl`
* `unrealized_pnl`
* `total_pnl`
* `total_delta`
* `total_gamma`
* `total_theta`
* `total_vega`
* `open_positions_count`
* `closed_positions_count`
* `new_positions_count`
* `underlying_price`
* `iv`

---

## Scelte architetturali confermate

### Dataclass runtime separate dalle entity DB

Le dataclass di dominio **non vanno sostituite** con model SQLAlchemy.

Motivo:

* il runtime model serve alla simulazione
* il persistence model serve al reporting/storage

Quindi il pattern corretto è:

* dataclass per il motore
* entity SQLAlchemy per la persistenza
* mapping dominio -> entity nel loop di backtest

---

## Note operative emerse

* usare `min(leg.state.T for leg in position.legs)` e non `min(leg.state for leg in position.legs)`
* `closed_at` richiede un `date`, non una stringa
* i model SQLAlchemy con `relationship("ClassName")` richiedono che tutte le classi siano importate all’avvio
* per evitare circular import usare `TYPE_CHECKING` e stringhe nelle relationship

---

## Prossimi step naturali

1. estrarre mapper/helper di persistenza
2. introdurre trade log esplicito
3. integrare il segnale macro solo in apertura
4. sostituire l’entry fissa con execution policy
5. aggiungere metriche aggregate per regime e strategia
6. introdurre rollout strutturato
7. evolvere la IV da proxy semplice a modello più ricco

---

## Stato attuale

Il sistema ha già definito:

* pricing engine base
* greche base
* runtime model per posizioni e portafoglio
* close logic minima
* caricamento dati da DB
* struttura di persistenza per trade, snapshot e performance
* scheletro funzionante del loop di backtest

La fase successiva è consolidare il salvataggio puntuale nel ciclo e rendere la strategia guidata da segnali di regime.
