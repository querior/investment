"""
Migrazione: processed_indicators
- Aggiunge colonna invert (boolean, default false)

Eseguire una volta prima di riavviare il backend.
"""
from app.db.session import engine
from sqlalchemy import text

def run():
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE processed_indicators ADD COLUMN IF NOT EXISTS invert BOOLEAN NOT NULL DEFAULT FALSE"
        ))
        conn.commit()
    print("Migrazione completata.")

if __name__ == "__main__":
    run()
