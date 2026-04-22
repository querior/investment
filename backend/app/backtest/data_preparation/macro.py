import pandas as pd
from app.services.pillars.service import compute_macro_risk_score


def add_macro_features(df: pd.DataFrame, db) -> pd.DataFrame:
    """
    Add macro features (macro_score, macro_regime) to dataframe.

    Args:
        df: DataFrame with 'date' column
        db: Database session

    Returns:
        pd.DataFrame: DataFrame with added 'macro_score' and 'macro_regime' columns
    """
    df = df.copy()

    macro_scores = []
    macro_regimes = []

    for date in df["date"]:
        macro_score, macro_regime = compute_macro_risk_score(db, date.date())
        macro_scores.append(macro_score)
        macro_regimes.append(macro_regime)

    df["macro_score"] = macro_scores
    df["macro_regime"] = macro_regimes

    return df
