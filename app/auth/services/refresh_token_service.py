from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.auth.models.refresh_token import RefreshToken
from app.core.security import generate_refresh_token, hash_refresh_token
from app.core.config import settings
from app.core.time import utcnow
from app.database.atomic import atomic


class RefreshTokenService:
    @staticmethod
    def create(db: Session, user_id: int) -> str:
        raw_token = generate_refresh_token()
        token_hash = hash_refresh_token(raw_token)

        refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=utcnow() + timedelta(hours=9),
        )

        with atomic(db):
            db.add(refresh_token)

        return raw_token

    @staticmethod
    def validate(db: Session, raw_token: str) -> RefreshToken | None:
        token_hash = hash_refresh_token(raw_token)

        token = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.token_hash == token_hash,
                RefreshToken.is_revoked.is_(False),
                RefreshToken.expires_at > utcnow(),
            )
            .first()
        )

        return token

    @staticmethod
    def revoke_all_for_user(db: Session, user_id: int) -> None:
        """Revoga os tokens do usuário na transação corrente (sem commit).

        É sempre chamado no meio de uma troca de senha, então quem delimita a
        operação é que faz o commit.
        """
        db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked.is_(False),
        ).update({"is_revoked": True})
