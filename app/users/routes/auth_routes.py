from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session, selectinload

from app.auth.services.refresh_token_service import RefreshTokenService
from app.core.security import create_access_token
from app.database.deps import get_db
from app.users.models.user import User
from app.users.models.role import Role
from app.users.models.menu_group import MenuGroup
from app.users.schemas.auth_schema import TokenResponse, LoginRequest
from app.users.schemas.user_schema import UserResponse
from app.users.services.auth_service import AuthService
from app.users.dependencies.auth_dependencies import get_current_user

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_me(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return current authenticated user with roles and permissions (e.g. after F5)."""
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    user = (
        db.query(User)
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.roles).selectinload(Role.menu_groups).selectinload(MenuGroup.permissions),
        )
        .filter(
            User.id == current_user.id,
            User.is_deleted.is_(False),
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


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

