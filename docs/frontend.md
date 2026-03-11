# Frontend — Decisioni e stato

## Stack tecnico

| Categoria | Scelta | Motivazione |
|-----------|--------|-------------|
| Framework | React 18 | — |
| Linguaggio | TypeScript 5 | Type safety |
| Build tool | Vite 5 | Dev server veloce |
| Package manager | pnpm 9 | — |
| State management | Redux Toolkit + Redux Saga | Separazione side effects (chiamate API) dallo stato |
| Routing | React Router v6 | — |
| UI component library | Ant Design 5 | — |
| CSS utility | Tailwind CSS 3 | — |
| HTTP client | Axios | Interceptor per auth token |

---

## Architettura

### Struttura cartelle

```
frontend/src/
├── app/
│   ├── index.tsx      # Provider: store, router
│   └── router.tsx     # Definizione route
├── auth/
│   ├── login-redirect.tsx   # Redirect a /login se non autenticato
│   └── protected.tsx        # HOC: wrappa le route protette
├── components/
│   └── chat/          # Chat widget floating (UI presente, backend da collegare)
├── features/
│   ├── auth/          # reducer + saga login/logout
│   └── scenario/      # reducer + saga fetch scenari
├── layout/
│   └── AppLayout.tsx  # Sidebar + header (Ant Design)
├── pages/
│   ├── Dashboard.tsx  # Card Long / Medium / Short con link alle pagine Live
│   ├── Data.tsx       # placeholder
│   ├── Backtest.tsx   # placeholder
│   ├── LiveLong.tsx   # placeholder
│   ├── LiveMedium.tsx # placeholder
│   ├── LiveShort.tsx  # placeholder
│   └── Settings.tsx   # placeholder
├── services/
│   ├── api.ts         # Axios instance, base URL, setAuthToken()
│   ├── auth-service.ts
│   └── scenario-service.ts
└── store/
    ├── index.ts       # Configura store Redux
    ├── reducers.ts    # combineReducers
    └── saga.ts        # rootSaga (fork di tutti i watcher)
```

### Route

| Path | Pagina | Stato |
|------|--------|-------|
| `/` | Dashboard | struttura base |
| `/analysis/data` | Data | placeholder |
| `/analysis/backtest` | Backtest | placeholder |
| `/live/long` | LiveLong | placeholder |
| `/live/medium` | LiveMedium | placeholder |
| `/live/short` | LiveShort | placeholder |
| `/settings` | Settings | placeholder |
| `/login` | Login | completo |

### Flusso auth

```
Login form → loginRequest (action)
  → loginSaga → POST /auth/login
  → token salvato in localStorage + header Axios
  → redirect /

Logout → logoutSaga
  → token rimosso da localStorage
  → redirect /login
```

Il token viene letto da localStorage anche al reload della pagina (`api.ts`).

### Connessione al backend

Base URL configurata in `services/api.ts`:

```
http://localhost:8000/api/v1
```

Vedi [`docs/operations.md`](./operations.md) per avviare il backend.

---

## Stato implementazione

### Completato
- [x] Login flow (form → Redux/Saga → token → redirect)
- [x] Auth guard e route protection
- [x] AppLayout (sidebar collapsibile + header con logout)
- [x] Fetch scenari dal backend
- [x] Chat widget (UI, risposte mock)
- [x] Dashboard con tre card Long / Medium / Short
- [x] Tutte le route collegate al menu (analysis/data, analysis/backtest, live/long, live/medium, live/short)

### Placeholder (struttura presente, contenuto da costruire)
- [ ] Dashboard — dati reali da collegare
- [ ] Data — visualizzazione dati macro e mercato
- [ ] Backtest — lancio e risultati backtest
- [ ] Live Long — allocation target, pillar scores, regime corrente
- [ ] Live Medium — stato layer medium
- [ ] Live Short — segnali, posizioni aperte, P&L
- [ ] Settings — configurazione utente e sistema

### Da costruire
- [ ] Visualizzazione allocation target e pillar scores (Live Long)
- [ ] Lancio e risultati backtest (Backtest)
- [ ] Integrazione chat con backend
- [ ] Grafici (libreria da scegliere — vedi Decisioni aperte)

---

## Decisioni aperte

- [ ] Come esporre i dati del Layer Long (polling? websocket? server-sent events?)
- [ ] Internazionalizzazione (IT/EN)?
- [ ] Grafici: libreria da scegliere (Recharts? Chart.js? Victory?)
- [ ] Mobile: condividere logica con React Native Expo o tenere separato?

---

## Riferimenti

- [`docs/architecture.md`](./architecture.md) — architettura generale del sistema
- [`docs/operations.md`](./operations.md) — come avviare backend e ambienti
- [`docs/requirements.md`](./requirements.md) — requisiti funzionali per layer
