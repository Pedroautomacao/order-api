from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.security import hash_password
from app.database.deps import get_db
from app.users.models.user import User
from app.users.models.role import Role
from app.users.schemas.user_schema import (
    UserCreate,
    UserUpdate,
    UserResponse, ResetPasswordRequest,
)
from app.users.services.user_service import UserService
from app.users.dependencies.permission_dependencies import require_permission
from app.users.dependencies.auth_dependencies import get_current_user

router = APIRouter()


@router.post(
    "/",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("user:create"))],
)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return UserService.create(
        db=db,
        data=data,
        current_user=current_user,
    )


@router.get(
    "/",
    response_model=list[UserResponse],
    dependencies=[Depends(require_permission("user:create"))],
)
def list_users(db: Session = Depends(get_db)):
    return (
        db.query(User)
        .options(
            selectinload(User.roles).selectinload(Role.permissions)
        )
        .filter(User.is_deleted.is_(False))
        .order_by(User.username)
        .all()
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("user:create"))],
)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .options(
            selectinload(User.roles).selectinload(Role.permissions)
        )
        .filter(
            User.id == user_id,
            User.is_deleted.is_(False),
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("user:update"))],
)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = (
        db.query(User)
        .options(
            selectinload(User.roles).selectinload(Role.permissions)
        )
        .filter(
            User.id == user_id,
            User.is_deleted.is_(False),
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserService.update(
        db=db,
        user=user,
        data=data,
        current_user=current_user,
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("user:delete"))],
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own user",
        )

    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.is_deleted.is_(False),
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    UserService.delete(
        db=db,
        user=user,
        current_user=current_user,
    )


@router.put(
    "/{user_id}/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("user:reset_password"))],
)
def reset_user_password(
    user_id: int,
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.is_deleted.is_(False),
        )
        .first()
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    UserService.reset_password(
        db=db,
        user=user,
        new_password=data.new_password,
        admin_user=current_user,
    )
