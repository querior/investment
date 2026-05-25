export type StrategyMeta = { acronym: string; color: string };

const STRATEGY_MAP: Record<string, StrategyMeta> = {
  bull_put_spread:           { acronym: "BPS",     color: "blue" },
  bear_call_spread:          { acronym: "BCS",     color: "orange" },
  put_broken_wing_butterfly: { acronym: "Put BWB", color: "lime" },
  bull_call_spread:          { acronym: "BuCS",    color: "cyan" },
  bear_put_spread:           { acronym: "BePS",    color: "purple" },
  long_straddle:             { acronym: "Std",     color: "gold" },
  long_strangle:             { acronym: "Sng",     color: "volcano" },
  iron_condor:               { acronym: "IC",      color: "green" },
  iron_butterfly:            { acronym: "IB",      color: "geekblue" },
  calendar_spread:           { acronym: "Cal",     color: "magenta" },
  jade_lizard:               { acronym: "JL",      color: "red" },
  reverse_jade_lizard:       { acronym: "RJL",     color: "pink" },
  diagonal_spread:           { acronym: "Diag",    color: "default" },
};

export function getStrategyMeta(type: string | null | undefined): StrategyMeta | null {
  if (!type) return null;
  return STRATEGY_MAP[type] ?? null;
}
