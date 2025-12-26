from sqlalchemy.orm import Session

from app.core.security import verify_password, create_access_token
from app.users.models.user import User
from app.auth.services.refresh_token_service import RefreshTokenService


class AuthService:
    @staticmethod
    def authenticate_user(
        db: Session,
        username: str,
        password: str,
    ) -> dict | None:
        user = (
            db.query(User)
            .filter(
                User.username == username,
                User.is_deleted.is_(False),
                User.is_active.is_(True),
            )
            .first()
        )

        if not user or not verify_password(password, user.password_hash):
            return None

        access_token = create_access_token(subject=str(user.id))
        refresh_token = RefreshTokenService.create(db, user.id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
        }
