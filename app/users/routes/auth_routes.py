from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.users.schemas.auth_schema import LoginRequest, TokenResponse
from app.users.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    print(data)
    token = AuthService.authenticate_user(
        db=db,
        email=data.email,
        password=data.password,
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return TokenResponse(access_token=token)
