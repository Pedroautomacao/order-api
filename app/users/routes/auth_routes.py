from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.services.refresh_token_service import RefreshTokenService
from app.core.security import create_access_token
from app.database.deps import get_db
from app.users.schemas.auth_schema import TokenResponse, LoginRequest
from app.users.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    tokens = AuthService.authenticate_user(
        db=db,
        username=data.username,
        password=data.password,
    )

    if not tokens:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db),
):
    token = RefreshTokenService.validate(db, refresh_token)

    if not token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    access_token = create_access_token(subject=str(token.user_id))

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }

