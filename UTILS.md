# Scenario Lab (FastAPI + React)

## Quickstart

### 1) Start DB + backend
```bash
docker compose up -d  (--build)
```

### 3) Seed a user
```bash
docker compose exec backend python -m app.scripts.seed_user demo@example.com password123
```

### 4) Frontend
```bash
cd frontend
pnpm i
pnpm run dev
```

Login with `demo@example.com / password123`.

## Utils

Per vedere i log di un container
docker logs -f <running-container-name>


## Interazione Claude

"Leggi CLAUDE.md e tutti i file in docs/ — stiamo lavorando al progetto investment"

Resume: claude --resume d3bca77a-be7c-4b8c-a51c-3b57b44e85eb
