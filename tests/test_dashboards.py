"""Painéis: recorte de período, taxas e apontamentos de ciclo anulado."""
from datetime import date, datetime, time, timedelta
from uuid import uuid4

import pytest

from app.analytics.service import _break_rate
from app.dashboard.services.dashboard_billing_service import DashboardBillingService
from app.dashboard.services.dashboard_breaks_service import DashboardBreaksService
from app.dashboard.services.dashboard_clients_service import DashboardClientsService
from app.dashboard.services.dashboard_overview_service import DashboardService
from app.dashboard.services.dashboard_production_service import DashboardProductionService
from app.dashboard.services.dashboard_products_service import DashboardProductsService
from app.dashboard.utils.date_range import resolve_datetime_range
from app.order_item_breaks.models import OrderItemBreak
from app.orders.enums import OrderItemStatus, OrderStatus
from app.orders.models.work_item import WorkItem
from app.orders.models.work_order import WorkOrder
from app.ranking.services.rankings_service import RankingsService

from tests.conftest import make_order
from app.core.time import today_sp

HOJE = today_sp()
# meio da tarde: dentro do dia, e fora do [00:00, 00:00] que o código antigo montava
MEIO_DIA = datetime.combine(HOJE, time(14, 0))


@pytest.fixture()
def base(catalog):
    """1 Produced, 2 Billed, 1 Canceled e 1 Awaiting hoje; 1 atraso + 1 cancelado antigo."""
    db = catalog.db
    pedidos = {}

    def novo(chave, status, sched=None, produto=None, item_status=OrderItemStatus.PRODUCED):
        pedidos[chave] = make_order(
            catalog,
            status=status,
            scheduled_date=sched,
            products=[produto or catalog.alfa],
            item_status=item_status,
        )

    novo("produzido", OrderStatus.PRODUCED)
    novo("faturado_1", OrderStatus.BILLED)
    novo("faturado_2", OrderStatus.BILLED, produto=catalog.zulu)
    novo("cancelado", OrderStatus.CANCELED, item_status=OrderItemStatus.AWAITING)
    novo("aguardando", OrderStatus.AWAITING, item_status=OrderItemStatus.AWAITING)
    novo(
        "atrasado",
        OrderStatus.AWAITING,
        sched=HOJE - timedelta(days=5),
        item_status=OrderItemStatus.AWAITING,
    )
    novo(
        "atrasado_cancelado",
        OrderStatus.CANCELED,
        sched=HOJE - timedelta(days=5),
        item_status=OrderItemStatus.AWAITING,
    )

    # apontamentos com hora real, não meia-noite
    for chave in ("produzido", "faturado_1", "faturado_2"):
        order = pedidos[chave]
        item = order.items[0]
        db.add(
            WorkOrder(
                order_id=order.id,
                user_id=catalog.user.id,
                started_at=MEIO_DIA,
                ended_at=MEIO_DIA + timedelta(minutes=30),
                time_to_produced_secs=1800,
            )
        )
        db.add(
            WorkItem(
                order_id=order.id,
                order_item_id=item.id,
                product_id=item.product_id,
                user_id=catalog.user.id,
                started_at=MEIO_DIA,
                ended_at=MEIO_DIA + timedelta(minutes=20),
                time_to_produced_secs=1200,
            )
        )

    produzido = pedidos["produzido"]
    db.add(
        OrderItemBreak(
            id=uuid4(),
            order_id=produzido.id,
            order_item_id=produzido.items[0].id,
            expected_quantity=10,
            confirmed_quantity=8,
            difference_quantity=2,
            created_at=MEIO_DIA,
            created_by=catalog.user.id,
        )
    )
    db.commit()
    return pedidos


class TestRecorteDePeriodo:
    """Colunas DateTime comparadas com `date` colapsam na meia-noite e zeram tudo."""

    def test_range_cobre_o_dia_inteiro(self):
        inicio, fim = resolve_datetime_range(None, None)

        assert fim - inicio >= timedelta(hours=23)

    def test_tempo_medio_de_producao_aparece(self, catalog, base):
        painel = DashboardProductionService.get(catalog.db)

        assert painel["avg_order_time_secs"] == 1800.0
        assert painel["avg_item_time_secs"] == 1200.0

    def test_quebras_aparecem(self, catalog, base):
        assert DashboardBreaksService.get(catalog.db)["total_lost_quantity"] == 2.0

    def test_producoes_por_produto_aparecem(self, catalog, base):
        produtos = DashboardProductsService.get(catalog.db)["products"]

        alfa = next(p for p in produtos if p["product_name"] == "Alfa")
        assert alfa["total_productions"] == 2
        assert alfa["avg_item_production_time_secs"] == 1200.0


class TestTaxaDeFaturamento:
    def test_nao_passa_de_cem_por_cento(self, catalog, base):
        """Produced e Billed são disjuntos: faturar tirava do denominador."""
        painel = DashboardBillingService.get(catalog.db)

        assert painel["billing_rate_percent"] == 66.67
        assert painel["billing_rate_percent"] <= 100

    def test_conta_produzidos_e_faturados(self, catalog, base):
        painel = DashboardBillingService.get(catalog.db)

        assert painel["produced_orders"] == 1
        assert painel["billed_orders"] == 2


class TestAtrasados:
    def test_cancelado_nao_e_atraso(self, catalog, base):
        assert DashboardService.overview(catalog.db)["overdue_orders"] == 1

    def test_ranking_de_atrasos_tambem_ignora_cancelado(self, catalog, base):
        rank = RankingsService.get(catalog.db)["top_clients_by_delays"]

        assert {r["name"]: r["value"] for r in rank}[catalog.client.name] == 1


class TestTaxaDeConclusao:
    """Faturar não pode derrubar a conclusão; cancelado sai da base."""

    def test_geral(self, catalog, base):
        # 1 produzido + 2 faturados, sobre 4 (5 de hoje menos 1 cancelado)
        assert DashboardService.overview(catalog.db)["completion_rate_today"] == 75.0

    def test_por_cliente(self, catalog, base):
        cliente = DashboardClientsService.get(catalog.db)["clients"][0]

        assert cliente["completion_rate_percent"] == 75.0
        assert cliente["avg_production_time_secs"] == 1800.0


class TestRanking:
    def test_volume_respeita_periodo_e_status(self, catalog, base):
        volume = {
            r["name"]: r["value"]
            for r in RankingsService.get(catalog.db)["top_products_by_volume"]
        }

        assert volume["Alfa"] == 10.0, "1 produzido + 1 faturado, sem o cancelado"

    def test_volume_ignora_pedido_fora_do_periodo(self, catalog, base):
        make_order(
            catalog,
            status=OrderStatus.PRODUCED,
            scheduled_date=HOJE - timedelta(days=60),
            products=[catalog.alfa],
            item_status=OrderItemStatus.PRODUCED,
            quantity=999,
        )

        volume = {
            r["name"]: r["value"]
            for r in RankingsService.get(catalog.db)["top_products_by_volume"]
        }

        assert volume["Alfa"] == 10.0


class TestApontamentoAnulado:
    @pytest.fixture()
    def produto_em_producao(self, catalog):
        from app.orders.services.order_service import OrderService

        make_order(catalog, products=[catalog.alfa])
        order = OrderService.assign_next_order(catalog.db, current_user=catalog.user)
        return order

    def test_produto_aparece_em_producao(self, catalog, produto_em_producao):
        produtos = DashboardProductsService.get(catalog.db)["products"]

        alfa = next(p for p in produtos if p["product_name"] == "Alfa")
        assert alfa["producing_now"] is True

    def test_reset_tira_o_produto_de_em_producao(self, catalog, produto_em_producao):
        """O reset zera ended_at: sem filtrar is_deleted, ficava marcado para sempre."""
        from app.orders.services.order_reset_service import OrderResetService

        OrderResetService.reset(
            db=catalog.db, order=produto_em_producao, current_user=catalog.user
        )

        produtos = DashboardProductsService.get(catalog.db)["products"]
        alfa = next(p for p in produtos if p["product_name"] == "Alfa")
        assert alfa["producing_now"] is False


class TestTaxaDeQuebra:
    def test_denominador_usa_status_do_item(self, catalog, base):
        """O reset grava produced_quantity = 0, não NULL: o item voltava a contar."""
        from app.orders.models.order import Order
        from app.orders.models.order_item import OrderItem

        inicio, fim = HOJE - timedelta(days=1), HOJE + timedelta(days=1)

        taxa = _break_rate(catalog.db, inicio, fim, None)

        esperado = (
            catalog.db.query(OrderItem)
            .join(Order, Order.id == OrderItem.order_id)
            .filter(
                OrderItem.status == OrderItemStatus.PRODUCED,
                Order.scheduled_date.between(inicio, fim),
            )
            .count()
        )
        assert taxa["produced_items"] == esperado
