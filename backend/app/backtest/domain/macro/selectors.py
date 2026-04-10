def classify_macro_regime(macro_score: float) -> str:
  if macro_score >= 0.5:
      return "RISK_ON"
  if macro_score <= -0.5:
      return "RISK_OFF"
  return "NEUTRAL"