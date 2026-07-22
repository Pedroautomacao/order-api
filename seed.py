"""
Seed rico do Uai System — popula o banco com dados que exercitam TODOS os casos
da plataforma: clientes com cada combinação de meios de pagamento e limites de
crédito, produtos com preços (ativos/inativos), e pedidos em todos os status
(aguardando, em produção, produzido, faturado, cancelado), à vista e a prazo,
pagos e pendentes, incluindo pedidos atrasados e um cliente no limite de crédito.

Uso (a partir de order-api/, com a venv):
    DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/order_api" \
        .venv/Scripts/python.exe seed.py

O script é idempotente: apaga os dados transacionais (pedidos, work orders,
quebras) e recria clientes/produtos/usuários de seed a cada execução. Roles,
permissões e unidades pré-existentes são preservados.
"""
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/order_api",
)
os.environ.setdefault("SECRET_KEY", "super-secret-key-change-me")

from app.database.session import SessionLocal  # noqa: E402
from app.database.imports import *  # noqa: F401,F403,E402  (carrega todos os modelos)
from app.core.security import hash_password  # noqa: E402
from app.clients.models.client import Client  # noqa: E402
from app.products.models.product import Product  # noqa: E402
from app.units.models.unit_of_measure import UnitOfMeasure  # noqa: E402
from app.users.models.user import User  # noqa: E402
from app.users.models.role import Role  # noqa: E402
from app.orders.models.order import Order  # noqa: E402
from app.orders.models.order_item import OrderItem  # noqa: E402
from app.orders.models.work_order import WorkOrder  # noqa: E402
from app.orders.models.work_item import WorkItem  # noqa: E402
from app.order_item_breaks.models.order_Item_break import OrderItemBreak  # noqa: E402
from app.orders.enums import OrderStatus, OrderItemStatus, PaymentMethod  # noqa: E402

BR = timezone(timedelta(hours=-3))
TODAY = date.today()


def utcnow():
    return datetime.now(timezone.utc)


# CPFs/CNPJs e SKUs que pertencem ao seed (o resto é considerado lixo de teste)
SEED_CLIENT_DOCS = {
    "12345678000190", "98765432000110", "11222333000181",
    "44555666000172", "77888999000163", "10101010000110",
}
SEED_PRODUCT_SKUS = {
    "BOV-PIC", "BOV-ALC", "BOV-COS", "AVE-FRA", "SUI-LIN",
    "SUI-BAC", "OVO-C30", "ACS-CAR", "OLD-001",
}


def wipe_transactional(db):
    """Remove dados transacionais e registros de teste para reexecução limpa."""
    db.query(OrderItemBreak).delete()
    db.query(WorkItem).delete()
    db.query(WorkOrder).delete()
    db.query(OrderItem).delete()
    db.query(Order).delete()
    db.commit()
    # remove clientes/produtos que não pertencem ao seed (sobras de testes)
    db.query(Product).filter(~Product.sku.in_(SEED_PRODUCT_SKUS)).delete(synchronize_session=False)
    db.query(Client).filter(~Client.cpf_cnpj.in_(SEED_CLIENT_DOCS)).delete(synchronize_session=False)
    db.commit()


def get_or_create_user(db, *, username, first, last, cpf, email, role_name):
    role = db.query(Role).filter(Role.name == role_name).first()
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(
            username=username,
            first_name=first,
            last_name=last,
            cpf=cpf,
            email=email,
            password_hash=hash_password("admin"),
            is_active=True,
        )
        db.add(user)
        db.flush()
    # define EXATAMENTE o perfil desejado (evita usuário de seed acumular perfis)
    user.roles = [role] if role else []
    return user


def upsert_unit(db, code, name):
    u = db.query(UnitOfMeasure).filter(UnitOfMeasure.code == code).first()
    if not u:
        u = UnitOfMeasure(code=code, name=name, is_active=True)
        db.add(u)
        db.flush()
    return u


def upsert_product(db, *, name, sku, price, unit, active=True, description=None):
    p = db.query(Product).filter(Product.sku == sku).first()
    if not p:
        p = Product(sku=sku)
        db.add(p)
    p.name = name
    p.unit_price = Decimal(str(price))
    p.unit_of_measure_id = unit.id
    p.is_active = active
    p.description = description
    p.is_deleted = False
    db.flush()
    return p


def upsert_client(db, *, name, cpf_cnpj, priority, allow_cash, allow_credit,
                  credit_limit, active=True):
    c = db.query(Client).filter(Client.cpf_cnpj == cpf_cnpj).first()
    if not c:
        c = Client(cpf_cnpj=cpf_cnpj)
        db.add(c)
    c.name = name
    c.priority = priority
    c.address = "Rua das Indústrias, 100 - MG"
    c.phone_number = "(31) 99999-0000"
    c.allow_cash = allow_cash
    c.allow_credit = allow_credit
    c.credit_limit = Decimal(str(credit_limit))
    c.is_active = active
    c.is_deleted = False
    db.flush()
    return c


def make_order(db, *, client, seller, status, payment_method, is_paid,
               items, scheduled_offset_days=0, producer=None):
    """Cria um pedido completo com itens e total. `items` = [(product, qty, produced_qty)]."""
    total = sum(Decimal(str(p.unit_price)) * Decimal(str(q)) for p, q, _ in items)
    order = Order(
        client_id=client.id,
        created_by_user_id=seller.id,
        assigned_user_id=producer.id if producer else None,
        priority=client.priority,
        status=status,
        scheduled_date=TODAY + timedelta(days=scheduled_offset_days),
        payment_method=payment_method,
        is_paid=is_paid,
        total_amount=total,
    )
    db.add(order)
    db.flush()

    created_items = []
    producing_marked = False
    for product, qty, produced in items:
        if status == OrderStatus.AWAITING:
            item_status = OrderItemStatus.AWAITING
            produced = None
        elif status == OrderStatus.PRODUCING:
            # itens com produced definido = já produzidos; o PRIMEIRO sem produced
            # vira o item atual (PRODUCING); os demais ficam AWAITING.
            if produced is not None:
                item_status = OrderItemStatus.PRODUCED
            elif not producing_marked:
                item_status = OrderItemStatus.PRODUCING
                producing_marked = True
            else:
                item_status = OrderItemStatus.AWAITING
        else:  # PRODUCED / BILLED / CANCELED
            item_status = OrderItemStatus.PRODUCED if status != OrderStatus.CANCELED else OrderItemStatus.AWAITING
        oi = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=qty,
            produced_quantity=produced,
            status=item_status,
        )
        db.add(oi)
        created_items.append((oi, item_status, product))
    db.flush()

    # para pedidos em produção, abrir um WorkItem no item atual (PRODUCING)
    if status == OrderStatus.PRODUCING and producer:
        for oi, st, product in created_items:
            if st == OrderItemStatus.PRODUCING:
                db.add(WorkItem(
                    order_id=order.id,
                    order_item_id=oi.id,
                    product_id=product.id,
                    user_id=producer.id,
                    started_at=utcnow() - timedelta(minutes=10),
                ))
        db.flush()
    return order


def add_work_order(db, order, user, *, minutes_ago_start, duration_secs=None):
    """Cria um WorkOrder (produção). Sem ended_at = produzindo agora."""
    started = utcnow() - timedelta(minutes=minutes_ago_start)
    ended = None
    if duration_secs is not None:
        ended = started + timedelta(seconds=duration_secs)
    db.add(WorkOrder(
        order_id=order.id,
        user_id=user.id,
        started_at=started,
        ended_at=ended,
        time_to_produced_secs=duration_secs,
    ))
    db.flush()


def run():
    db = SessionLocal()
    try:
        print("Limpando dados transacionais...")
        wipe_transactional(db)

        print("Garantindo usuários (senha: admin)...")
        admin = get_or_create_user(db, username="admin", first="Admin", last="System",
                                   cpf="00000000000", email="admin@uaisystem.com", role_name="Admin")
        seller = get_or_create_user(db, username="vendedor", first="Vanessa", last="Vendas",
                                    cpf="11111111111", email="vendedor@uaisystem.com", role_name="Vendedor")
        producer = get_or_create_user(db, username="produtor", first="Pedro", last="Produção",
                                      cpf="22222222222", email="produtor@uaisystem.com", role_name="Produtor")
        get_or_create_user(db, username="fiscal", first="Fábio", last="Fiscal",
                           cpf="33333333333", email="fiscal@uaisystem.com", role_name="Fiscal")
        db.commit()

        print("Unidades e produtos...")
        kg = upsert_unit(db, "kg", "Quilograma")
        un = upsert_unit(db, "un", "Unidade")
        cx = upsert_unit(db, "cx", "Caixa")

        p_picanha = upsert_product(db, name="Picanha Peça", sku="BOV-PIC", price=79.90, unit=kg)
        p_alcatra = upsert_product(db, name="Alcatra Limpa", sku="BOV-ALC", price=42.50, unit=kg)
        p_costela = upsert_product(db, name="Costela Bovina", sku="BOV-COS", price=32.00, unit=kg)
        p_frango = upsert_product(db, name="Frango Inteiro", sku="AVE-FRA", price=12.90, unit=kg)
        p_linguica = upsert_product(db, name="Linguiça Toscana", sku="SUI-LIN", price=24.90, unit=kg)
        p_bacon = upsert_product(db, name="Bacon em Cubos", sku="SUI-BAC", price=28.00, unit=kg)
        p_ovos = upsert_product(db, name="Ovos (caixa 30)", sku="OVO-C30", price=18.00, unit=cx)
        p_carvao = upsert_product(db, name="Carvão 5kg", sku="ACS-CAR", price=22.00, unit=un)
        upsert_product(db, name="Produto Descontinuado", sku="OLD-001", price=9.99, unit=un, active=False)
        db.commit()

        print("Clientes (todas as combinações de pagamento e limite)...")
        # à vista e a prazo, limite alto
        c_super = upsert_client(db, name="Supermercado Minas", cpf_cnpj="12345678000190",
                                priority="B", allow_cash=True, allow_credit=True, credit_limit=5000)
        # ambas, limite baixo (fácil de estourar) — vamos deixá-lo NO limite
        c_rest = upsert_client(db, name="Restaurante Sabor de MG", cpf_cnpj="98765432000110",
                               priority="C", allow_cash=True, allow_credit=True, credit_limit=300)
        # só a prazo
        c_acougue = upsert_client(db, name="Açougue Central", cpf_cnpj="11222333000181",
                                  priority="C", allow_cash=False, allow_credit=True, credit_limit=1500)
        # só à vista
        c_church = upsert_client(db, name="Churrascaria do Gaúcho", cpf_cnpj="44555666000172",
                                 priority="D", allow_cash=True, allow_credit=False, credit_limit=0)
        # ambas, sem limite de crédito (0) — a prazo sempre barra
        c_merc = upsert_client(db, name="Mercadinho da Vila", cpf_cnpj="77888999000163",
                               priority="E", allow_cash=True, allow_credit=True, credit_limit=0)
        # cliente inativo
        upsert_client(db, name="Cliente Inativo Ltda", cpf_cnpj="10101010000110",
                      priority="F", allow_cash=True, allow_credit=True, credit_limit=1000, active=False)
        db.commit()

        print("Pedidos cobrindo todos os status e cenários de pagamento...")

        # ---- HOJE (alimentam o dashboard) ----
        # Aguardando, à vista
        make_order(db, client=c_super, seller=seller, status=OrderStatus.AWAITING,
                   payment_method=PaymentMethod.CASH, is_paid=False,
                   items=[(p_picanha, 10, None), (p_frango, 20, None)])
        # Aguardando, a prazo (conta no limite do supermercado)
        make_order(db, client=c_super, seller=seller, status=OrderStatus.AWAITING,
                   payment_method=PaymentMethod.CREDIT, is_paid=False,
                   items=[(p_alcatra, 15, None)])
        # Em produção (produzindo agora) — produtor com work order aberto
        o_prod = make_order(db, client=c_acougue, seller=seller, status=OrderStatus.PRODUCING,
                            payment_method=PaymentMethod.CREDIT, is_paid=False, producer=producer,
                            items=[(p_costela, 30, 30.0), (p_linguica, 12, None)])
        add_work_order(db, o_prod, producer, minutes_ago_start=25)  # sem fim = produzindo agora
        # Produzido hoje, a prazo NÃO pago
        o_pnb = make_order(db, client=c_acougue, seller=seller, status=OrderStatus.PRODUCED,
                           payment_method=PaymentMethod.CREDIT, is_paid=False, producer=producer,
                           items=[(p_bacon, 8, 8.0)])
        add_work_order(db, o_pnb, producer, minutes_ago_start=180, duration_secs=1500)
        # Faturado hoje, à vista pago
        make_order(db, client=c_super, seller=seller, status=OrderStatus.BILLED,
                   payment_method=PaymentMethod.CASH, is_paid=True, producer=producer,
                   items=[(p_ovos, 40, 40.0)])
        # Cancelado hoje
        make_order(db, client=c_merc, seller=seller, status=OrderStatus.CANCELED,
                   payment_method=PaymentMethod.CASH, is_paid=False,
                   items=[(p_carvao, 50, None)])

        # ---- Restaurante NO LIMITE (limite 300; deixa ~290 em aberto a prazo não pago) ----
        make_order(db, client=c_rest, seller=seller, status=OrderStatus.PRODUCED,
                   payment_method=PaymentMethod.CREDIT, is_paid=False, producer=producer,
                   items=[(p_picanha, 2, 2.0), (p_linguica, 5, 5.0)])  # ~289,50

        # ---- ATRASADOS (scheduled_date no passado, ainda não produzidos) ----
        make_order(db, client=c_church, seller=seller, status=OrderStatus.AWAITING,
                   payment_method=PaymentMethod.CASH, is_paid=False, scheduled_offset_days=-2,
                   items=[(p_costela, 20, None)])
        make_order(db, client=c_acougue, seller=seller, status=OrderStatus.PRODUCING,
                   payment_method=PaymentMethod.CREDIT, is_paid=False, producer=producer,
                   scheduled_offset_days=-1, items=[(p_frango, 15, None)])

        # ---- HISTÓRICO (dias anteriores, produzidos/faturados — alimentam gráficos) ----
        for d in range(2, 9):
            o_hist = make_order(db, client=c_super, seller=seller,
                                status=OrderStatus.BILLED if d % 2 else OrderStatus.PRODUCED,
                                payment_method=PaymentMethod.CASH if d % 2 else PaymentMethod.CREDIT,
                                is_paid=bool(d % 2), producer=producer, scheduled_offset_days=-d,
                                items=[(p_alcatra, 5 + d, float(5 + d))])
            add_work_order(db, o_hist, producer, minutes_ago_start=d * 600,
                           duration_secs=1200 + d * 60)

        # ---- Pedido a prazo PAGO (não conta no limite) para o açougue ----
        make_order(db, client=c_acougue, seller=seller, status=OrderStatus.BILLED,
                   payment_method=PaymentMethod.CREDIT, is_paid=True, producer=producer,
                   scheduled_offset_days=-3, items=[(p_bacon, 10, 10.0)])

        # ---- Quebra de produção (produzido menor que o previsto) ----
        o_break = make_order(db, client=c_super, seller=seller, status=OrderStatus.PRODUCED,
                             payment_method=PaymentMethod.CASH, is_paid=True, producer=producer,
                             scheduled_offset_days=-1, items=[(p_picanha, 10, 8.5)])
        item = db.query(OrderItem).filter(OrderItem.order_id == o_break.id).first()
        import uuid
        db.add(OrderItemBreak(
            id=uuid.uuid4(),
            order_id=o_break.id,
            order_item_id=item.id,
            expected_quantity=Decimal("10.000"),
            confirmed_quantity=Decimal("8.500"),
            difference_quantity=Decimal("1.500"),
        ))

        db.commit()

        # Resumo
        counts = {s.value: db.query(Order).filter(Order.status == s).count() for s in OrderStatus}
        print("\n[OK] Seed concluido!")
        print("   Clientes:", db.query(Client).count(), "| Produtos:", db.query(Product).count())
        print("   Pedidos por status:", counts)
        print("   Total de pedidos:", db.query(Order).count())
        print("\n   Logins (senha: admin): admin, vendedor, produtor, fiscal")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run()
