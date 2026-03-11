"""Seed a demo user.

Run inside backend container:
python -m app.scripts.seed_user demo@example.com password123
"""
import sys
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.services.user_service import create_user, get_user_by_email

def main():
    if len(sys.argv) != 3:
        print("Usage: python -m app.scripts.seed_user <email> <password>")
        raise SystemExit(1)
    email, password = sys.argv[1], sys.argv[2]
    db: Session = SessionLocal()
    try:
        existing = get_user_by_email(db, email)
        if existing:
            print("User already exists:", email)
            return
        create_user(db, email, password)
        print("Created user:", email)
    finally:
        db.close()

if __name__ == "__main__":
    main()
