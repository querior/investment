"""
Migrazione: macro_processed
- Aggiunge colonna z_score_ema (float, nullable)
- Rimuove colonna z_score_percentile (non utilizzata)

Eseguire una volta prima di riavviare il backend.
"""
from app.db.session import engine
from sqlalchemy import text

def run():
    with engine.connect() as conn:
        # Aggiunge z_score_ema se non esiste già
        conn.execute(text(
            "ALTER TABLE macro_processed ADD COLUMN IF NOT EXISTS z_score_ema FLOAT"
        ))
        # Rimuove z_score_percentile se esiste
        conn.execute(text(
            "ALTER TABLE macro_processed DROP COLUMN IF EXISTS z_score_percentile"
        ))
        conn.commit()
    print("Migrazione completata.")

if __name__ == "__main__":
    run()
