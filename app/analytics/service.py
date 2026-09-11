"""
Serviço de Analytics — agregações de pedidos por range de data para a tela de
Engenharia de Dados. Dois recortes:
  - overview(): visão geral (todos os clientes)
  - by_client(): comportamento de um cliente específico

Reaproveita os modelos de Order/OrderItem/Product/Client/User e os enums.
"""
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.orders.enums import OrderItemStatus, OrderStatus, PaymentMethod
from app.orders.models.order import Order
from app.orders.models.order_item import OrderItem
from app.order_item_breaks.models.order_Item_break import OrderItemBreak
from app.products.models.product import Product
from app.clients.models.client import Client
from app.users.models.user import User
from app.core.time import today_sp


PRODUCED_LIKE = (OrderStatus.PRODUCED, OrderStatus.BILLED)


def _base_orders(db: Session, start: date, end: date):
    return db.query(Order).filter(
        Order.scheduled_date.between(start, end),
        Order.is_deleted.is_(False),
    )


def _status_counts(q):
    rows = q.with_entities(Order.status, func.count(Order.id)).group_by(Order.status).all()
    counts = {s.value: 0 for s in OrderStatus}
    for status, n in rows:
        counts[status.value if hasattr(status, "value") else status] = n
    return counts


def _orders_by_day(db, start: date, end: date, client_id: int | None):
    q = db.query(Order.scheduled_date, func.count(Order.id)).filter(
        Order.scheduled_date.between(start, end),
        Order.is_deleted.is_(False),
    )
    if client_id:
        q = q.filter(Order.client_id == client_id)
    rows = dict(q.group_by(Order.scheduled_date).all())
    days = []
    d = start
    while d <= end:
        days.append({"date": d.isoformat(), "count": int(rows.get(d, 0))})
        d += timedelta(days=1)
    return days


def _top_skus(db, start: date, end: date, client_id: int | None, limit=10):
    q = (
        db.query(
            Product.sku,
            Product.name,
            func.sum(OrderItem.quantity).label("qty"),
            func.count(OrderItem.id).label("lines"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            Order.scheduled_date.between(start, end),
            Order.is_deleted.is_(False),
            Order.status != OrderStatus.CANCELED,
        )
    )
    if client_id:
        q = q.filter(Order.client_id == client_id)
    rows = (
        q.group_by(Product.id, Product.sku, Product.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
        .all()
    )
    return [
        {"sku": sku, "name": name, "quantity": float(qty or 0), "lines": int(lines)}
        for sku, name, qty, lines in rows
    ]


def _financials(q):
    """Soma total, faturado, em aberto (a prazo não pago) e ticket médio."""
    total_amount = q.with_entities(func.coalesce(func.sum(Order.total_amount), 0)).filter(
        Order.status != OrderStatus.CANCELED
    ).scalar() or 0
    n_valid = q.with_entities(func.count(Order.id)).filter(
        Order.status != OrderStatus.CANCELED
    ).scalar() or 0
    billed_amount = q.with_entities(func.coalesce(func.sum(Order.total_amount), 0)).filter(
        Order.status == OrderStatus.BILLED
    ).scalar() or 0
    outstanding = q.with_entities(func.coalesce(func.sum(Order.total_amount), 0)).filter(
        Order.payment_method == PaymentMethod.CREDIT,
        Order.is_paid.is_(False),
        Order.status != OrderStatus.CANCELED,
    ).scalar() or 0
    avg_ticket = (Decimal(str(total_amount)) / n_valid) if n_valid else Decimal("0")
    return {
        "total_amount": float(total_amount),
        "billed_amount": float(billed_amount),
        "outstanding_amount": float(outstanding),
        "avg_ticket": float(round(avg_ticket, 2)),
    }


def _payment_mix(q):
    rows = q.with_entities(Order.payment_method, func.count(Order.id)).filter(
        Order.status != OrderStatus.CANCELED
    ).group_by(Order.payment_method).all()
    mix = {"cash": 0, "credit": 0}
    for pm, n in rows:
        key = "credit" if (getattr(pm, "value", pm) == PaymentMethod.CREDIT.value) else "cash"
        mix[key] = n
    return mix


def _break_rate(db, start: date, end: date, client_id: int | None):
    """Taxa de quebra: itens com quebra / itens produzidos, no range."""
    breaks_q = (
        db.query(func.count(OrderItemBreak.id))
        .join(Order, Order.id == OrderItemBreak.order_id)
        .filter(
            Order.scheduled_date.between(start, end),
            Order.is_deleted.is_(False),
            OrderItemBreak.is_deleted.is_(False),
        )
    )
    produced_items_q = (
        db.query(func.count(OrderItem.id))
        .join(Order, Order.id == OrderItem.order_id)
        .filter(
            Order.scheduled_date.between(start, end),
            Order.is_deleted.is_(False),
            # o status e a fonte de verdade: o reset grava produced_quantity = 0
            # (nao NULL), entao o item voltava a contar como produzido
            OrderItem.status == OrderItemStatus.PRODUCED,
        )
    )
    if client_id:
        breaks_q = breaks_q.filter(Order.client_id == client_id)
        produced_items_q = produced_items_q.filter(Order.client_id == client_id)
    breaks = breaks_q.scalar() or 0
    produced = produced_items_q.scalar() or 0
    rate = (breaks / produced * 100) if produced else 0
    return {"breaks": int(breaks), "produced_items": int(produced), "rate": round(rate, 1)}


class AnalyticsService:
    @staticmethod
    def overview(db: Session, *, start: date, end: date):
        q = _base_orders(db, start, end)
        counts = _status_counts(q)
        total = sum(counts.values())
        completion = (counts[OrderStatus.PRODUCED.value] + counts[OrderStatus.BILLED.value]) / total * 100 if total else 0

        # top vendedores (por pedidos produzidos+faturados)
        seller_rows = (
            db.query(User.first_name, User.last_name, func.count(Order.id))
            .join(Order, Order.created_by_user_id == User.id)
            .filter(
                Order.scheduled_date.between(start, end),
                Order.is_deleted.is_(False),
                Order.status.in_(PRODUCED_LIKE),
            )
            .group_by(User.id, User.first_name, User.last_name)
            .order_by(func.count(Order.id).desc())
            .limit(8)
            .all()
        )
        top_sellers = [
            {"name": f"{fn} {ln}".strip(), "produced_orders": int(n)}
            for fn, ln, n in seller_rows
        ]

        # top clientes (por total de pedidos, com valor)
        client_rows = (
            db.query(
                Client.name,
                func.count(Order.id),
                func.coalesce(func.sum(Order.total_amount), 0),
            )
            .join(Order, Order.client_id == Client.id)
            .filter(
                Order.scheduled_date.between(start, end),
                Order.is_deleted.is_(False),
                Order.status != OrderStatus.CANCELED,
            )
            .group_by(Client.id, Client.name)
            .order_by(func.count(Order.id).desc())
            .limit(8)
            .all()
        )
        top_clients = [
            {"name": name, "orders": int(n), "amount": float(amount or 0)}
            for name, n, amount in client_rows
        ]

        return {
            "range": {"start": start.isoformat(), "end": end.isoformat()},
            "total_orders": total,
            "orders_by_status": counts,
            "completion_rate": round(completion, 1),
            "financials": _financials(q),
            "payment_mix": _payment_mix(q),
            "break_stats": _break_rate(db, start, end, None),
            "orders_by_day": _orders_by_day(db, start, end, None),
            "top_skus": _top_skus(db, start, end, None),
            "top_sellers": top_sellers,
            "top_clients": top_clients,
        }

    @staticmethod
    def by_client(db: Session, *, client_id: int, start: date, end: date):
        client = db.query(Client).filter(Client.id == client_id).first()
        q = _base_orders(db, start, end).filter(Order.client_id == client_id)
        counts = _status_counts(q)
        total = sum(counts.values())

        # dias desde o último pedido
        last = (
            db.query(func.max(Order.scheduled_date))
            .filter(Order.client_id == client_id, Order.is_deleted.is_(False))
            .scalar()
        )
        days_since_last = (today_sp() - last).days if last else None

        outstanding = q.with_entities(func.coalesce(func.sum(Order.total_amount), 0)).filter(
            Order.payment_method == PaymentMethod.CREDIT,
            Order.is_paid.is_(False),
            Order.status != OrderStatus.CANCELED,
        ).scalar() or 0

        credit_limit = float(client.credit_limit or 0) if client else 0

        return {
            "client": {
                "id": client.id,
                "name": client.name,
                "allow_cash": client.allow_cash,
                "allow_credit": client.allow_credit,
                "credit_limit": credit_limit,
            } if client else None,
            "range": {"start": start.isoformat(), "end": end.isoformat()},
            "total_orders": total,
            "orders_by_status": counts,
            "financials": _financials(q),
            "payment_mix": _payment_mix(q),
            "break_stats": _break_rate(db, start, end, client_id),
            "credit": {
                "limit": credit_limit,
                "outstanding": float(outstanding),
                "available": credit_limit - float(outstanding),
            },
            "days_since_last_order": days_since_last,
            "orders_by_day": _orders_by_day(db, start, end, client_id),
            "top_skus": _top_skus(db, start, end, client_id),
        }
