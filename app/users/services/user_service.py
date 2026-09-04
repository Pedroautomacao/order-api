from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.auth.services.refresh_token_service import RefreshTokenService
from app.database.atomic import atomic
from app.users.models.user import User
from app.users.models.role import Role
from app.users.models.menu_group import MenuGroup
from app.users.schemas.user_schema import UserCreate, UserUpdate
from app.core.security import hash_password, verify_password
from app.audit.services.audit_service import AuditService


class UserService:
    @staticmethod
    def create(
        db: Session,
        *,
        data: UserCreate,
        current_user: User,
    ) -> User:
        existing_username = db.query(User).filter(User.username == data.username.strip(), User.is_deleted.is_(False)).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um usuário com este nome de usuário (username).",
            )
        if data.email and data.email.strip():
            existing_email = db.query(User).filter(User.email == data.email.strip(), User.is_deleted.is_(False)).first()
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este e-mail já está em uso.",
                )
        existing_cpf = db.query(User).filter(User.cpf == data.cpf.strip(), User.is_deleted.is_(False)).first()
        if existing_cpf:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Já existe um usuário com este CPF.",
            )

        user = User(
            username=data.username.strip(),
            first_name=data.first_name.strip(),
            last_name=data.last_name.strip(),
            cpf=data.cpf.strip(),
            email=data.email.strip() if data.email else None,
            password_hash=hash_password(data.password),
            is_active=data.is_active,
        )
        with atomic(db):
            db.add(user)
            db.flush()  # precisa do id gerado para vincular perfis e logar

            if getattr(data, "role_ids", None):
                roles = db.query(Role).filter(Role.id.in_(data.role_ids)).all()
                user.roles = roles

            AuditService.log(
                db=db,
                action="user:create",
                entity="user",
                entity_id=user.id,
                user_id=current_user.id,
                description=f"User {user.username} created by {current_user.username}",
            )

        # Load relationships
        return (
            db.query(User)
            .options(
                selectinload(User.roles).selectinload(Role.permissions),
                selectinload(User.roles).selectinload(Role.menu_groups).selectinload(MenuGroup.permissions),
            )
            .filter(User.id == user.id)
            .first()
        )

    @staticmethod
    def update(
        db: Session,
        *,
        user: User,
        data: UserUpdate,
        current_user: User,
    ) -> User:
        dump = data.model_dump(exclude_unset=True)
        role_ids = dump.pop("role_ids", None)
        password = dump.pop("password", None)

        if "email" in dump and dump["email"] and str(dump["email"]).strip():
            new_email = str(dump["email"]).strip()
            existing_email = (
                db.query(User)
                .filter(User.email == new_email, User.id != user.id, User.is_deleted.is_(False))
                .first()
            )
            if existing_email:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Este e-mail já está em uso.",
                )

        with atomic(db):
            for field, value in dump.items():
                setattr(user, field, value)

            if password is not None:
                user.password_hash = hash_password(password)

            if role_ids is not None:
                roles = db.query(Role).filter(Role.id.in_(role_ids)).all()
                user.roles = roles

            AuditService.log(
                db=db,
                action="user:update",
                entity="user",
                entity_id=user.id,
                user_id=current_user.id,
                description=f"User {user.username} updated by {current_user.username}",
            )

        # Load relationships
        return (
            db.query(User)
            .options(
                selectinload(User.roles).selectinload(Role.permissions),
                selectinload(User.roles).selectinload(Role.menu_groups).selectinload(MenuGroup.permissions),
            )
            .filter(User.id == user.id)
            .first()
        )

    @staticmethod
    def delete(
        db: Session,
        *,
        user: User,
        current_user: User,
    ) -> None:
        if user.is_deleted:
            return

        with atomic(db):
            user.is_deleted = True

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
        with atomic(db):
            user.password_hash = hash_password(new_password)

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

    @staticmethod
    def change_own_password(
            db: Session,
            *,
            user: User,
            current_password: str,
            new_password: str,
    ) -> None:
        """Troca da própria senha: exige a senha atual correta."""
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Senha atual incorreta.",
            )
        if verify_password(new_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A nova senha deve ser diferente da atual.",
            )

        with atomic(db):
            user.password_hash = hash_password(new_password)

            # revoga tokens antigos por segurança
            RefreshTokenService.revoke_all_for_user(db, user.id)

            AuditService.log(
                db=db,
                action="user:change_password",
                entity="user",
                entity_id=user.id,
                user_id=user.id,
                description=f"User '{user.username}' changed own password",
            )
