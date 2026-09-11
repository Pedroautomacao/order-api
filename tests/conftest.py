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


# ---------------------------------------------------------------------------
# Banco SQLite em memória — regras de negócio sem depender do Postgres
# ---------------------------------------------------------------------------

from datetime import date as _date, datetime as _datetime, time as _time, timedelta
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.database.imports import *  # noqa: F401,F403  (registra todos os modelos)
from app.core.time import today_sp
from app.clients.models.client import Client as _Client
from app.orders.enums import (
    OrderItemStatus,
    OrderStatus,
    PaymentMethod,
    ProductionApproval,
)
from app.orders.models.order import Order as _Order
from app.orders.models.order_item import OrderItem as _OrderItem
from app.products.models.product import Product as _Product
from app.units.models.unit_of_measure import UnitOfMeasure as _Unit
from app.users.models.user import User as _User


@pytest.fixture()
def sqlite_session(monkeypatch):
    """Sessão isolada em SQLite, criada a partir dos próprios modelos.

    Não toca o banco real e roda em qualquer máquina. O SQLite não guarda
    timezone (no Postgres as colunas são ``timestamptz``), então ``utcnow`` é
    trocado por uma versão naive nos módulos que subtraem datas — senão a conta
    estoura com "offset-naive and offset-aware datetimes".
    """
    from app.orders.services import (
        order_finish_service,
        order_item_service,
        order_service,
    )

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    for mod in (order_item_service, order_service, order_finish_service):
        monkeypatch.setattr(mod, "utcnow", lambda: _datetime.utcnow())

    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def catalog(sqlite_session):
    """Usuário, cliente, unidade e dois produtos (Alfa e Zulu, nessa ordem alfabética)."""
    db = sqlite_session

    user = _User(
        username="produtor",
        first_name="Produtor",
        last_name="Teste",
        cpf="000",
        password_hash="x",
        is_active=True,
    )
    client = _Client(
        name="Cliente Teste",
        priority="A",
        # sem dígitos que colidam com ids pequenos: a busca por id usa OR com
        # LIKE em nome e CNPJ, e "123" casaria com o pedido de id 1, 2 ou 3
        cpf_cnpj="00.000.000/0000-00",
        address="Rua 1",
        phone_number="9",
        observations="",
        is_active=True,
        allow_cash=True,
        allow_credit=True,
        credit_limit=999999,
    )
    unit = _Unit(code="kg", name="Quilo", is_active=True)
    db.add_all([user, client, unit])
    db.flush()

    alfa = _Product(
        name="Alfa", sku="A", is_active=True, unit_price=10, unit_of_measure_id=unit.id
    )
    zulu = _Product(
        name="Zulu", sku="Z", is_active=True, unit_price=20, unit_of_measure_id=unit.id
    )
    db.add_all([alfa, zulu])
    db.commit()

    return SimpleNamespace(
        db=db, user=user, client=client, unit=unit, alfa=alfa, zulu=zulu
    )


def make_order(
    cat,
    *,
    status=OrderStatus.AWAITING,
    scheduled_date=None,
    products=None,
    item_status=OrderItemStatus.AWAITING,
    quantity=5,
    production_approval=ProductionApproval.APPROVED,
):
    """Cria um pedido direto no banco, sem passar pelas validações do service.

    Nasce aprovado de propósito: quase todo teste quer um pedido que já pode
    ser produzido. Quem testa a trava de liberação passa o valor explícito.
    """
    db = cat.db

    order = _Order(
        client_id=cat.client.id,
        created_by_user_id=cat.user.id,
        priority="A",
        status=status,
        production_approval=production_approval,
        scheduled_date=scheduled_date or today_sp(),
        payment_method=PaymentMethod.CASH,
        is_paid=False,
        total_amount=100,
    )
    db.add(order)
    db.flush()

    for product in products or [cat.zulu, cat.alfa]:
        db.add(
            _OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                unit_price=product.unit_price or 0,
                produced_quantity=(
                    quantity if item_status == OrderItemStatus.PRODUCED else None
                ),
                status=item_status,
            )
        )
    db.commit()
    return order


def confirm_next_item(cat, order, produced_quantity=None):
    """Confirma o item que está em produção, como faz a tela do produtor."""
    from app.orders.services.order_item_service import OrderItemService

    item = next(i for i in order.items if i.status == OrderItemStatus.PRODUCING)
    payload = SimpleNamespace(
        produced_quantity=produced_quantity if produced_quantity is not None else item.quantity
    )
    return OrderItemService.confirm_item(
        cat.db, order_item_id=item.id, data=payload, current_user=cat.user
    )
