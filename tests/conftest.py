"""
Configuração de testes para a order-api.

Pré-requisitos:
  pip install -r requirements-test.txt

Execução:
  pytest

O banco de testes usa a mesma DATABASE_URL configurada no .env.
Cada teste roda dentro de uma transação que é revertida ao final,
garantindo isolamento sem sujar o banco real.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, create_access_token
from app.database.base import Base
from app.database.deps import get_db
from app.users.models.user import User
from app.users.models.role import Role
from app.users.models.permission import Permission
from app.users.models.menu_group import MenuGroup


# ---------------------------------------------------------------------------
# Engine de testes — usa o mesmo banco, mas opera dentro de transação revertida
# ---------------------------------------------------------------------------

test_engine = create_engine(settings.database_url, pool_pre_ping=True)


@pytest.fixture(scope="function")
def db():
    """
    Sessão de banco de dados isolada por teste.
    Todas as escritas são revertidas ao final, sem afetar dados reais.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db):
    """
    TestClient com `get_db` substituído pela sessão de teste isolada.
    O scheduler de startup é ignorado via monkeypatch implícito do TestClient.
    """
    from app.main import app

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    # Desativa o scheduler durante testes
    app.router.on_startup.clear()

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helpers para criar dados de teste
# ---------------------------------------------------------------------------

def make_role(db: Session, name: str) -> Role:
    role = Role(name=name)
    db.add(role)
    db.flush()
    return role


def make_permission(db: Session, code: str) -> Permission:
    perm = Permission(code=code, name=code, description=code)
    db.add(perm)
    db.flush()
    return perm


def make_user(
    db: Session,
    username: str = "testuser",
    password: str = "testpass",
    role: Role | None = None,
    cpf: str = "000.000.000-00",
) -> User:
    user = User(
        username=username,
        email=f"{username}@test.com",
        first_name="Test",
        last_name="User",
        cpf=cpf,
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.flush()
    if role:
        user.roles.append(role)
        db.flush()
    return user


def auth_headers_for(user: User) -> dict:
    token = create_access_token(subject=str(user.id))
    return {"Authorization": f"Bearer {token}"}
