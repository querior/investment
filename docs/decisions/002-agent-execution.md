# ADR 002 — Architettura agente di esecuzione per il trading semi-automatico

**Data**: 2026-03-10
**Status**: futura — da riprendere quando il sistema è maturo

## Contesto
Quando il sistema sarà maturo, il layer Short dovrà poter eseguire operazioni
in modo semi-automatico o automatico tramite API del broker.
Occorre decidere come strutturare il componente di esecuzione.

## Decisione
Adottare un'architettura ad **agente con azioni limitate e strategia come configurazione parametrica**.

L'agente non ha logica decisionale propria — esegue esclusivamente dentro
i vincoli della strategia configurata dall'utente.

## Motivazioni
- Separazione netta tra logica decisionale (strategia) e logica di esecuzione (agente)
- I parametri di rischio sono enforced a livello architetturale, non come semplici check
- La modalità semi-automatica (conferma umana) è un caso degenerato della stessa architettura, non un sistema separato
- Più facile da testare: la strategia è un oggetto serializzabile, l'agente è stateless

## Struttura della strategia (parametri minimi)
```json
{
  "instrument": "option_call | option_put | etf | future",
  "entry_signals": [...],
  "exit_signals": [...],
  "capital_per_trade": "% del capitale disponibile",
  "max_risk_per_trade": "% massima di perdita accettabile",
  "max_open_positions": 1,
  "mode": "manual | semi_auto | auto",
  "broker_account": "..."
}
```

## Azioni consentite all'agente
- `open_position(strategy, signal)` — apre una posizione nei limiti della strategia
- `close_position(strategy, position_id)` — chiude una posizione esistente
- `request_confirmation(trade_proposal)` — in modalità semi_auto, notifica e attende
- `log_action(action, outcome)` — logga ogni operazione

Qualsiasi azione fuori da questo set richiede intervento esplicito dell'utente.

## Trade-off accettati
- Meno flessibile di un sistema completamente programmabile
- Richiede una fase di design accurata dei parametri della strategia prima dell'implementazione
- L'integrazione con l'API del broker è ancora da definire (dipende dal broker scelto)

## Alternative scartate
- **Sistema rule-based classico (if/then hardcoded)**: meno flessibile, difficile da configurare senza modificare il codice
- **Agente con piena autonomia decisionale**: rischio operativo troppo elevato, non adatto a questo contesto

## Decisioni aperte
- [ ] Quale broker e quale API (probabile IBKR, da confermare)
- [ ] Gestione errori e fallback se l'API del broker non risponde
- [ ] Notifiche all'utente in modalità semi_auto (email, push, Telegram?)
- [ ] Audit log: dove e come conservare lo storico delle operazioni eseguite