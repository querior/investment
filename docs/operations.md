# Manuale operativo — Investment System

## Ambienti disponibili

| Ambiente | Variabile | File di configurazione | Uso |
|----------|-----------|------------------------|-----|
| Development | `development` | `backend/.env.dev` | Sviluppo locale, default |
| Test | `test` | `backend/.env.test` | Esecuzione test, CI |
| Production | `production` | `backend/.env.prod` | Deploy live |

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
├── .env.dev     # development
├── .env.test    # test
├── .env.prod    # production
└── .env.example # template di riferimento
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
