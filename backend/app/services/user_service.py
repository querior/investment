from sqlalchemy.orm import Session
from app.db.user import User
from app.core.security import hash_password, verify_password

def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).one_or_none()

def create_user(db: Session, email: str, password: str) -> User:
    u = User(email=email, password_hash=hash_password(password))
    db.add(u)
    db.commit()
    db.refresh(u)
    return u

def verify_user(db: Session, email: str, password: str) -> bool:
    u = get_user_by_email(db, email)
    if not u:
        return False
    return verify_password(password, u.password_hash)
