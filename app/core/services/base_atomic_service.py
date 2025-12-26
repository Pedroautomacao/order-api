from sqlalchemy.orm import Session
from app.database.atomic import atomic


class BaseAtomicService:
    @staticmethod
    def run_atomic(db: Session, fn):
        with atomic(db):
            return fn()
