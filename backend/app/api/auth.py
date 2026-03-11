from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.deps import get_db
from app.schemas.auth import LoginRequest, TokenResponse
from app.core.security import create_access_token
from app.services.user_service import verify_user

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    ok = verify_user(db, payload.email, payload.password)
    if not ok:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(subject=payload.email)
    return TokenResponse(access_token=token)
