"""
Migrazione: asset_classes
- Aggiunge colonna min_weight (float, default 0.0)

Eseguire una volta prima di riavviare il backend.
"""
from app.db.session import engine
from sqlalchemy import text

def run():
    with engine.connect() as conn:
        conn.execute(text(
            "ALTER TABLE asset_classes ADD COLUMN IF NOT EXISTS min_weight FLOAT NOT NULL DEFAULT 0.0"
        ))
        conn.commit()
    print("Migrazione completata.")

if __name__ == "__main__":
    run()
