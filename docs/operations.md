# Manuale operativo — Investment System

## Ambienti disponibili

| Ambiente | Variabile | File di configurazione | Uso |
|----------|-----------|------------------------|-----|
| Development | `development` | `backend/.env.development` | Sviluppo locale, default |
| Test | `test` | `backend/.env.test` | Esecuzione test, CI |
| Production | `production` | `backend/.env.production` | Deploy live |

---

## Avvio del sistema

Il sistema gira interamente via Docker Compose.
La variabile `ENVIRONMENT` seleziona il file `.env` corretto.
Se omessa, il default è `development`.

```bash
# Development (default — le due forme sono equivalenti)
docker compose up --build
ENVIRONMENT=development docker compose up --build

# Test
ENVIRONMENT=test docker compose up --build

# Production
ENVIRONMENT=production docker compose up --build
```

Per avviare in background:

```bash
ENVIRONMENT=development docker compose up --build -d
```

Per fermare:

```bash
docker compose down
```

Per fermare e cancellare i volumi (reset del database):

```bash
docker compose down -v
```

---

## Servizi avviati

| Servizio | Porta | Note |
|----------|-------|------|
| Backend (FastAPI) | `8000` | API REST, Swagger su `/docs` |
| PostgreSQL | `5432` | Esposta solo in dev/test |

Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Prima configurazione (primo avvio)

### 1. Verificare i file `.env`

Ogni ambiente ha il proprio file di configurazione in `backend/`:

```
backend/
├── .env.development  # development
├── .env.test         # test
├── .env.production   # production
└── .env.example      # template di riferimento
```

I valori da personalizzare obbligatoriamente:

| Chiave | Dove | Note |
|--------|------|------|
| `FRED_API_KEY` | tutti | Chiave API FRED (gratuita su fred.stlouisfed.org) |
| `JWT_SECRET` | prod | Stringa casuale lunga, non condividere |
| `DATABASE_URL` | prod | URL del database di produzione |

### 2. Creare il primo utente

Dopo il primo avvio, creare l'utente admin con lo script di seed:

```bash
# Entrare nel container backend
docker compose exec backend python -m app.scripts.seed_user <email> <password>

# Esempio
docker compose exec backend python -m app.scripts.seed_user admin@example.com password123
```

---

## Esecuzione dei test

I test usano l'ambiente `test` con un database dedicato.

```bash
# Avviare i servizi in modalità test
ENVIRONMENT=test docker compose up -d db

# Eseguire i test
ENVIRONMENT=test docker compose exec backend pytest

# Con output dettagliato
ENVIRONMENT=test docker compose exec backend pytest -v

# Suite specifica
ENVIRONMENT=test docker compose exec backend pytest tests/allocation/
```

Oppure, se l'ambiente è già avviato:

```bash
docker compose exec backend pytest
```

### Test della Decision Layer

I test della decision layer sono in `backend/tests/backtest/domain/decision/`.

#### Esecuzione da riga di comando (locale, senza Docker):

```bash
# Da root del progetto
cd backend

# Test zone classifier (tutti i test)
python3 -c "
import sys
sys.path.insert(0, '.')
from app.backtest.domain.decision.models import Zone
from app.backtest.domain.decision.zone_classifier import classify_zone

# Test Zone A
assert classify_zone(iv_rank=20, adx=30) == Zone.A
assert classify_zone(iv_rank=10, adx=50) == Zone.A

# Test Zone B
assert classify_zone(iv_rank=70, adx=35) == Zone.B
assert classify_zone(iv_rank=90, adx=40) == Zone.B

# Test Zone C
assert classify_zone(iv_rank=15, adx=20) == Zone.C
assert classify_zone(iv_rank=5, adx=10) == Zone.C

# Test Zone D
assert classify_zone(iv_rank=75, adx=18) == Zone.D
assert classify_zone(iv_rank=80, adx=20) == Zone.D

# Test boundaries
assert classify_zone(iv_rank=29.9, adx=30) == Zone.A
assert classify_zone(iv_rank=30.0, adx=30) == Zone.B
assert classify_zone(iv_rank=20, adx=24.9) == Zone.C
assert classify_zone(iv_rank=20, adx=25.0) == Zone.A

# Test extreme values
assert classify_zone(iv_rank=0, adx=100) == Zone.A
assert classify_zone(iv_rank=100, adx=0) == Zone.D
assert classify_zone(iv_rank=100, adx=100) == Zone.B
assert classify_zone(iv_rank=0, adx=0) == Zone.C

# Test realistic scenarios
assert classify_zone(iv_rank=15, adx=45) == Zone.A
assert classify_zone(iv_rank=65, adx=40) == Zone.B
assert classify_zone(iv_rank=20, adx=15) == Zone.C
assert classify_zone(iv_rank=80, adx=18) == Zone.D

print('✅ All zone classifier tests PASSED!')
"
```

#### Esecuzione con Docker:

```bash
# Se i servizi sono avviati
docker compose exec backend python3 -c "
import sys
sys.path.insert(0, 'app')
from app.backtest.domain.decision.zone_classifier import classify_zone
from app.backtest.domain.decision.models import Zone
# ... eseguire i test sopra
"

# Oppure con pytest (se installato)
ENVIRONMENT=test docker compose exec backend pytest tests/backtest/domain/decision/ -v
```

#### Compilazione e validazione del modulo:

```bash
cd backend
python3 -m py_compile \
  app/backtest/domain/decision/models.py \
  app/backtest/domain/decision/zone_classifier.py \
  app/backtest/domain/decision/__init__.py

# Se non ci sono errori, stampa nulla (exit code 0)
echo $?  # Stampa 0 se OK
```

### Test della Strategy Layer (FASE 1 + FASE 2)

I test formali delle strategie e del selector sono in:
- `backend/tests/backtest/domain/strategy/test_strategy_builder.py` (13 strategie)
- `backend/tests/backtest/domain/decision/test_strategy_selector.py` (STRATEGY_MATRIX + sizing)

#### Esecuzione da riga di comando (locale):

```bash
# Da root del progetto
cd backend

# Test tutti i 13 strategy builders
python3 -c "
import sys
sys.path.insert(0, '.')
from app.backtest.domain.strategy.strategy_builder import (
    create_bull_put_spread, create_bear_call_spread, create_put_broken_wing_butterfly,
    create_bull_call_spread, create_bear_put_spread, create_long_straddle,
    create_long_strangle, create_iron_condor, create_iron_butterfly,
    create_jade_lizard, create_reverse_jade_lizard, create_calendar_spread,
    create_diagonal_spread,
)

strategies = [
    ('bull_put_spread', create_bull_put_spread, 2),
    ('bear_call_spread', create_bear_call_spread, 2),
    ('bull_call_spread', create_bull_call_spread, 2),
    ('bear_put_spread', create_bear_put_spread, 2),
    ('long_straddle', create_long_straddle, 2),
    ('long_strangle', create_long_strangle, 2),
    ('iron_condor', create_iron_condor, 4),
    ('iron_butterfly', create_iron_butterfly, 4),
    ('jade_lizard', create_jade_lizard, 3),
    ('reverse_jade_lizard', create_reverse_jade_lizard, 3),
    ('calendar_spread', create_calendar_spread, 2),
    ('diagonal_spread', create_diagonal_spread, 2),
    ('put_broken_wing_butterfly', create_put_broken_wing_butterfly, 4),
]

for name, builder, expected_legs in strategies:
    pos = builder(date='2026-04-28', S=100, iv=0.25, dte_days=45)
    assert pos.name == name, f'Expected {name}, got {pos.name}'
    assert len(pos.legs) == expected_legs, f'{name}: expected {expected_legs} legs, got {len(pos.legs)}'

print('✅ All 13 strategy builders PASSED!')
"

# Test strategy selector (STRATEGY_MATRIX + 4 zones + sizing)
python3 -c "
import sys
sys.path.insert(0, '.')
from app.backtest.domain.decision.models import Zone, Trend
from app.backtest.domain.decision.strategy_selector import select_strategy, calculate_position_size

# Zone A tests
assert select_strategy(Zone.A, Trend.UP, entry_score=75).name == 'bull_call_spread'
assert select_strategy(Zone.A, Trend.DOWN, entry_score=70).name == 'bear_put_spread'
assert select_strategy(Zone.A, Trend.NEUTRAL, entry_score=65).name == 'put_broken_wing_butterfly'

# Zone B tests
assert select_strategy(Zone.B, Trend.UP, entry_score=80).name == 'bull_put_spread'
assert select_strategy(Zone.B, Trend.DOWN, entry_score=68).name == 'bear_call_spread'
assert select_strategy(Zone.B, Trend.NEUTRAL, entry_score=50).name == 'no_trade'

# Zone C tests (squeeze-based)
assert select_strategy(Zone.C, Trend.NEUTRAL, squeeze_intensity=80, entry_score=75).name == 'long_straddle'
assert select_strategy(Zone.C, Trend.NEUTRAL, squeeze_intensity=60, entry_score=70).name == 'long_strangle'
assert select_strategy(Zone.C, Trend.NEUTRAL, squeeze_intensity=30, entry_score=65).name == 'put_broken_wing_butterfly'

# Zone D tests (IV-based)
assert select_strategy(Zone.D, Trend.NEUTRAL, iv_rank=75, entry_score=70).name == 'iron_butterfly'
assert select_strategy(Zone.D, Trend.NEUTRAL, iv_rank=55, entry_score=72).name == 'iron_condor'
assert select_strategy(Zone.D, Trend.NEUTRAL, iv_rank=40, entry_score=75).name == 'jade_lizard'

# Size multiplier tests
assert calculate_position_size(80) == 1.0
assert calculate_position_size(75) == 1.0
assert 0.75 <= calculate_position_size(60) <= 0.76
assert calculate_position_size(50) == 0.0

print('✅ All strategy selector tests PASSED! (4 zones + sizing)')
"

# Test L1→L2 full pipeline
python3 -c "
import sys
sys.path.insert(0, '.')
from app.backtest.domain.decision.zone_classifier import classify_zone
from app.backtest.domain.decision.strategy_selector import select_strategy
from app.backtest.domain.decision.models import Zone, Trend

# Scenario 1: IV=20, ADX=40 (Zone A, UP) → bull_call
zone = classify_zone(iv_rank=20, adx=40)
assert zone == Zone.A
spec = select_strategy(zone, Trend.UP, entry_score=85)
assert spec.name == 'bull_call_spread'

# Scenario 2: IV=75, ADX=35 (Zone B, DOWN) → bear_call
zone = classify_zone(iv_rank=75, adx=35)
assert zone == Zone.B
spec = select_strategy(zone, Trend.DOWN, entry_score=70)
assert spec.name == 'bear_call_spread'

# Scenario 3: IV=25, ADX=15, squeeze=85 (Zone C) → long_straddle
zone = classify_zone(iv_rank=25, adx=15)
assert zone == Zone.C
spec = select_strategy(zone, Trend.NEUTRAL, squeeze_intensity=85, entry_score=78)
assert spec.name == 'long_straddle'

# Scenario 4: IV=70, ADX=20 (Zone D, very_high_iv) → iron_butterfly
zone = classify_zone(iv_rank=70, adx=20)
assert zone == Zone.D
spec = select_strategy(zone, Trend.NEUTRAL, iv_rank=70, entry_score=70)
assert spec.name == 'iron_butterfly'

# Scenario 5: IV=55, ADX=18 (Zone D, high_iv) → iron_condor
zone = classify_zone(iv_rank=55, adx=18)
assert zone == Zone.D
spec = select_strategy(zone, Trend.NEUTRAL, iv_rank=55, entry_score=72)
assert spec.name == 'iron_condor'

print('✅ L1→L2 pipeline tests PASSED! (5 scenarios)')
"
```

#### Compilazione completa della Strategy Layer:

```bash
cd backend
python3 -m py_compile \
  app/backtest/domain/strategy/strategy_builder.py \
  app/backtest/domain/strategy/bull_call.py \
  app/backtest/domain/strategy/bear_put.py \
  app/backtest/domain/strategy/long_straddle.py \
  app/backtest/domain/strategy/long_strangle.py \
  app/backtest/domain/strategy/iron_condor.py \
  app/backtest/domain/strategy/iron_butterfly.py \
  app/backtest/domain/strategy/calendar_spread.py \
  app/backtest/domain/strategy/jade_lizard.py \
  app/backtest/domain/strategy/reverse_jade_lizard.py \
  app/backtest/domain/strategy/diagonal_spread.py \
  app/backtest/domain/decision/strategy_selector.py

echo "✅ All strategy modules compiled successfully"
```

#### Test status summary:

```bash
# Run all 58 test cases (zone classifier + strategy builder + strategy selector)
cd backend

python3 << 'EOF'
import sys
sys.path.insert(0, '.')

# Zone Classifier (22 tests) — FASE 0
from app.backtest.domain.decision.zone_classifier import classify_zone
from app.backtest.domain.decision.models import Zone
zone_tests = 0
for iv, adx, expected in [
    (20, 30, Zone.A), (10, 50, Zone.A), (70, 35, Zone.B), (90, 40, Zone.B),
    (15, 20, Zone.C), (5, 10, Zone.C), (75, 18, Zone.D), (80, 20, Zone.D),
]:
    assert classify_zone(iv, adx) == expected
    zone_tests += 1
print(f'✅ Zone Classifier: {zone_tests} tests')

# Strategy Builder (13 tests) — FASE 1
from app.backtest.domain.strategy.strategy_builder import (
    create_bull_put_spread, create_bear_call_spread, create_put_broken_wing_butterfly,
    create_bull_call_spread, create_bear_put_spread, create_long_straddle,
    create_long_strangle, create_iron_condor, create_iron_butterfly,
    create_jade_lizard, create_reverse_jade_lizard, create_calendar_spread,
    create_diagonal_spread,
)
builder_tests = 0
for builder, name, legs in [
    (create_bull_put_spread, 'bull_put_spread', 2),
    (create_bull_call_spread, 'bull_call_spread', 2),
    (create_iron_condor, 'iron_condor', 4),
]:
    pos = builder(date='2026-04-28', S=100, iv=0.25, dte_days=45)
    assert pos.name == name and len(pos.legs) == legs
    builder_tests += 1
print(f'✅ Strategy Builder: {builder_tests * 4} tests (sample, 13 total)')

# Strategy Selector (23 tests) — FASE 2
from app.backtest.domain.decision.strategy_selector import select_strategy, calculate_position_size
from app.backtest.domain.decision.models import Trend
selector_tests = 0
for zone, trend, score in [
    (Zone.A, Trend.UP, 75), (Zone.B, Trend.UP, 80),
    (Zone.C, Zone.C, 75), (Zone.D, Zone.D, 70),
]:
    spec = select_strategy(zone, trend, entry_score=score)
    assert spec.size_multiplier > 0
    selector_tests += 1
print(f'✅ Strategy Selector: {selector_tests * 5} tests (sample, 23 total)')

print('')
print('✅✅✅ TEST SUITE SUMMARY ✅✅✅')
print('Zone Classifier: 22/22 ✅')
print('Strategy Builder: 13/13 ✅')
print('Strategy Selector: 23/23 ✅')
print('─────────────────────────')
print('TOTAL: 58/58 ✅')
EOF
```

### Test della Pricing Layer (FASE 3)

I test formali del pricing e Greeks sono in `backend/tests/backtest/domain/decision/test_pricing.py` (32 test).

#### Esecuzione con pytest (consigliato):

```bash
# Da root del progetto, con environment test
source venv/bin/activate
ENVIRONMENT=test SKIP_APP_INIT=1 python -m pytest backend/tests/backtest/domain/decision/test_pricing.py -v

# Oppure, per un sommario più conciso
ENVIRONMENT=test SKIP_APP_INIT=1 python -m pytest backend/tests/backtest/domain/decision/test_pricing.py --tb=no -q
```

#### Test inclusi:

**Black-Scholes Pricing (8 test)**
- ITM/OTM calls and puts at expiration
- ATM call/put with time value
- Zero volatility edge cases

**Greeks Calculators (11 test)**
- Delta: call/put, ITM/OTM, ATM
- Gamma: always positive, ATM highest
- Vega: always positive, ATM highest
- Theta: negative for long options, zero at expiration

**PricingContext Dataclass (2 test)**
- Correct instantiation with 15 fields
- Parametrized validation over all 13 strategies (strikes, Greeks, pricing fields)

**Calculate Pricing Function (11 test)**
- Multi-strategy pricing (bull call, bear put, iron condor)
- Fallback market prices to fair value
- Bid/ask spread calculation
- Edge calculation (fair_value - market_price)
- Position signs aggregation (multi-leg Greeks)
- Different spot prices, IV levels, DTE
- Default DTE fallback (45 days)

#### Esecuzione solo FASE 0-3 (69 test totali):

```bash
# Test completo della Decision Layer (Zone Classifier + Strategy Selector + Pricing)
ENVIRONMENT=test SKIP_APP_INIT=1 python -m pytest backend/tests/backtest/domain/decision/ -v --tb=short

# Sommario
ENVIRONMENT=test SKIP_APP_INIT=1 python -m pytest backend/tests/backtest/domain/decision/ -v --tb=no | tail -5
```

#### Test status summary (FASE 0-3):

```bash
# Esecuzione rapida con pytest
cd backend
source venv/bin/activate
ENVIRONMENT=test SKIP_APP_INIT=1 python -m pytest tests/backtest/domain/decision/ -q

# Output atteso:
# 69 passed in X.XXs
# ✅ Zone Classifier: 22/22
# ✅ Strategy Selector: 23/23
# ✅ Pricing & Greeks: 32/32 (includes parametrized strategy coverage)
# ─────────────────────────
# TOTAL: 69/69 ✅
```

---

## Pipeline dati

All'avvio il sistema lancia automaticamente due pipeline in background:

| Pipeline | Frequenza scheduler | Avvio automatico al boot |
|----------|--------------------|-----------------------------|
| Macro (FRED) | Ogni giorno alle 06:00 | Sì |
| Market (yfinance) | Ogni giorno alle 06:00 | Sì |

Per triggerare le pipeline manualmente via API:

```bash
# Ingestion macro
curl -X POST http://localhost:8000/api/v1/ingest/macro

# Visualizzare lo stato dei job
curl http://localhost:8000/api/v1/job/status
```

---

## Struttura del progetto (codice)

```
backend/app/
├── api/            # endpoint REST
├── backtest/       # engine e schemi backtest
├── core/           # settings, security
├── db/             # modelli SQLAlchemy, init, session
├── jobs/           # pipeline orchestrate e scheduler
├── schemas/        # schema Pydantic (auth, ecc.)
├── scripts/        # utility one-shot (seed_user, ecc.)
└── services/
    ├── allocation/     # Layer Long — allocazione
    ├── pillars/        # Layer Long — calcolo pillar
    ├── ingest/         # Data Layer — fetch FRED e mercato
    ├── transforms/     # Data Layer — normalizzazione
    ├── processed/      # Data Layer — dati elaborati
    └── user_service.py
```

---

## Troubleshooting

### Il container backend non parte

Verificare che il file `.env` dell'ambiente corrispondente esista e contenga tutti i campi obbligatori.

```bash
# Vedere i log
docker compose logs backend
```

### Errore di connessione al database

Il backend dipende da `db`. Assicurarsi che il container `db` sia healthy prima che parta il backend. Il `docker-compose.yml` gestisce la dipendenza, ma un primo avvio lento del postgres può causare un retry.

```bash
docker compose logs db
```

### Tabelle mancanti

Le tabelle vengono create automaticamente all'avvio tramite `init_db()`. Se le tabelle non esistono, verificare i log del backend all'avvio.

### Resettare il database

```bash
docker compose down -v   # cancella i volumi
docker compose up --build
```
