from sqlalchemy.orm import Session

from app.auth.services.refresh_token_service import RefreshTokenService
from app.core.services.base_atomic_service import BaseAtomicService
from app.users.models.user import User
from app.users.schemas.user_schema import UserCreate, UserUpdate
from app.core.security import hash_password
from app.audit.services.audit_service import AuditService


class UserService(BaseAtomicService):
    @staticmethod
    def create(
        db: Session,
        *,
        data: UserCreate,
        current_user: User,
    ) -> User:
        user = User(
            username=data.username,
            first_name=data.first_name,
            last_name=data.last_name,
            cpf=data.cpf,
            email=data.email,
            password_hash=hash_password(data.password),
            is_active=data.is_active,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        AuditService.log(
            db=db,
            action="user:create",
            entity="user",
            entity_id=user.id,
            user_id=current_user.id,
            description=f"User {user.username} created by {current_user.username}",
        )

        return user

    @staticmethod
    def update(
        db: Session,
        *,
        user: User,
        data: UserUpdate,
        current_user: User,
    ) -> User:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)

        db.commit()
        db.refresh(user)

        AuditService.log(
            db=db,
            action="user:update",
            entity="user",
            entity_id=user.id,
            user_id=current_user.id,
            description=f"User {user.username} updated by {current_user.username}",
        )

        return user

    @staticmethod
    def delete(
        db: Session,
        *,
        user: User,
        current_user: User,
    ) -> None:
        if user.is_deleted:
            return

        user.is_deleted = True
        db.commit()

        AuditService.log(
            db=db,
            action="user:delete",
            entity="user",
            entity_id=user.id,
            user_id=current_user.id,
            description=f"User {user.username} soft deleted by {current_user.username} ",
        )

    @staticmethod
    def reset_password(
            db: Session,
            *,
            user: User,
            new_password: str,
            admin_user: User,
    ) -> None:
        user.password_hash = hash_password(new_password)
        db.commit()

        # revoke all refresh tokens
        RefreshTokenService.revoke_all_for_user(db, user.id)

        AuditService.log(
            db=db,
            action="user:reset_password",
            entity="user",
            entity_id=user.id,
            user_id=admin_user.id,
            description=(
                f"Password reset for user '{user.username}' "
                f"by admin '{admin_user.username}'"
            ),
        )
