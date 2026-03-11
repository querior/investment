# ADR 001 — Template per decisioni architetturali

## Come usare questa cartella
Ogni volta che prendi una decisione non ovvia (scelta di libreria, approccio tecnico,
trade-off consapevole) crea un file `NNN-titolo.md` in questa cartella.

Serve a te tra 6 mesi e a Claude in ogni nuova sessione.

---

# ADR 001 — Data Layer centralizzato vs fetch diretto per layer

**Data**: da compilare
**Status**: proposta

## Contesto
Ogni layer ha bisogno di dati di mercato. Si può fare fetch diretto in ogni layer
o centralizzare in un unico Data Layer.

## Decisione
Centralizzare nel Data Layer.

## Motivazioni
- Evita chiamate API duplicate (costi e rate limit)
- Un solo punto di normalizzazione del formato dati
- I layer possono lavorare su dati cached anche offline
- Più facile mockare i dati per i test

## Trade-off accettati
- Un po' più di struttura iniziale da costruire
- I layer dipendono dal Data Layer (dipendenza accettabile e unidirezionale)

## Alternative scartate
- Fetch diretto per layer: più semplice ma non scala, duplicazione logica
