# ADR 003 — Libreria grafici: Visx

**Data**: 2026-03-13
**Status**: deciso

## Contesto
Il sistema richiede grafici per layer con esigenze diverse:
- **Long/Medium**: line chart e bar chart per serie temporali macro, pillar scores, allocation weights
- **Short**: candlestick OHLCV con indicatori sovrapposti (SMA, RSI, MACD) su pannelli multipli

Serve un'unica libreria che copra tutti i casi senza dipendenze aggiuntive.

## Decisione
Usare **Visx** (by Airbnb, MIT) versione 3.12.

## Motivazioni
- Unica libreria per tutti i tipi di grafico necessari (line, bar, candlestick) — nessuna dipendenza aggiuntiva
- Wrapper React su D3: accesso diretto alle primitive (scale, shape, axis) con API React
- Tree-shakeable: si importa solo ciò che si usa (`@visx/shape`, `@visx/scale`, ecc.)
- Nessun conflitto di stile: renderizza SVG puro, compatibile con Ant Design e Tailwind
- Supporto nativo per tooltip, zoom, brush, legenda
- Open source MIT, no costi

## Pacchetti installati
```
@visx/shape @visx/group @visx/scale @visx/axis
@visx/grid @visx/tooltip @visx/responsive @visx/legend @visx/curve
```

## Pattern adottato
Componenti riutilizzabili in `frontend/src/components/charts/`:
- `Chart.tsx` — line e bar chart generico, accetta `series[]` con `type: "line" | "bar"`
- Futuro: `CandlestickChart.tsx` per il layer Short

## Alternative scartate
- **Recharts**: no candlestick nativo, meno flessibile
- **Lightweight Charts (TradingView)**: eccellente per candlestick ma non copre i grafici macro — due librerie invece di una
- **Nivo**: no candlestick, bundle pesante
- **Librerie a pagamento**: escluse a priori
