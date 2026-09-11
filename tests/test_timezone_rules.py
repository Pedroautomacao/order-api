"""Toda decisão de data e hora usa o fuso de São Paulo.

Os testes injetam o instante em vez de confiar no relógio da máquina: o host de
desenvolvimento roda em UTC-3, igual a São Paulo, então um bug de fuso passaria
batido aqui e só apareceria no container, que roda em UTC.
"""
from datetime import date, datetime, timedelta, timezone

import pytest

from app.core.time import (
    SAME_DAY_CUTOFF_HOUR,
    SAO_PAULO,
    allows_same_day_delivery,
    min_scheduled_date,
    today_sp,
)
from app.orders.exception_handler import InvalidScheduledDateException
from app.orders.schemas.order_item_schema import OrderItemCreate
from app.orders.schemas.order_schema import OrderCreate
from app.orders.services.order_service import OrderService

from tests.conftest import make_order


def congelar(monkeypatch, instante_sp: datetime):
    """Fixa o "agora" de São Paulo visto por app.core.time."""
    monkeypatch.setattr(
        "app.core.time.now_sp", lambda: instante_sp.replace(tzinfo=SAO_PAULO)
    )


class TestFusoNaoEODoContainer:
    def test_a_data_de_sao_paulo_difere_da_de_utc_a_noite(self):
        """23h42 em São Paulo já é o dia seguinte em UTC.

        É a janela em que date.today() no container devolvia amanhã e toda a
        lógica de "hoje" saía errada por um dia.
        """
        instante = datetime(2026, 9, 11, 2, 42, tzinfo=timezone.utc)

        assert instante.date() == date(2026, 9, 11)
        assert instante.astimezone(SAO_PAULO).date() == date(2026, 9, 10)

    def test_today_sp_usa_a_data_de_sao_paulo(self, monkeypatch):
        congelar(monkeypatch, datetime(2026, 9, 10, 23, 42))

        assert today_sp() == date(2026, 9, 10)


class TestCorteDas16h:
    @pytest.mark.parametrize("hora", [0, 8, 12, 15])
    def test_antes_das_16h_a_entrega_pode_ser_hoje(self, monkeypatch, hora):
        congelar(monkeypatch, datetime(2026, 9, 10, hora, 30))

        assert allows_same_day_delivery() is True
        assert min_scheduled_date() == date(2026, 9, 10)

    @pytest.mark.parametrize("hora", [16, 17, 23])
    def test_das_16h_em_diante_a_entrega_e_amanha(self, monkeypatch, hora):
        congelar(monkeypatch, datetime(2026, 9, 10, hora, 0))

        assert allows_same_day_delivery() is False
        assert min_scheduled_date() == date(2026, 9, 11)

    def test_a_virada_e_exatamente_as_16h(self, monkeypatch):
        congelar(monkeypatch, datetime(2026, 9, 10, 15, 59))
        assert min_scheduled_date() == date(2026, 9, 10)

        congelar(monkeypatch, datetime(2026, 9, 10, 16, 0))
        assert min_scheduled_date() == date(2026, 9, 11)

    def test_a_hora_do_corte_e_16(self):
        assert SAME_DAY_CUTOFF_HOUR == 16


class TestCriacaoDePedido:
    def _payload(self, catalog, quando):
        return OrderCreate(
            client_id=catalog.client.id,
            scheduled_date=quando,
            items=[OrderItemCreate(product_id=catalog.alfa.id, quantity=1)],
        )

    def test_aceita_entrega_hoje_antes_das_16h(self, catalog, monkeypatch):
        congelar(monkeypatch, datetime(2026, 9, 10, 9, 0))

        pedido = OrderService.create(
            catalog.db,
            data=self._payload(catalog, date(2026, 9, 10)),
            current_user=catalog.user,
        )

        assert pedido.scheduled_date == date(2026, 9, 10)

    def test_recusa_entrega_hoje_depois_das_16h(self, catalog, monkeypatch):
        congelar(monkeypatch, datetime(2026, 9, 10, 16, 30))

        with pytest.raises(InvalidScheduledDateException):
            OrderService.create(
                catalog.db,
                data=self._payload(catalog, date(2026, 9, 10)),
                current_user=catalog.user,
            )

    def test_depois_das_16h_amanha_continua_valendo(self, catalog, monkeypatch):
        congelar(monkeypatch, datetime(2026, 9, 10, 16, 30))

        pedido = OrderService.create(
            catalog.db,
            data=self._payload(catalog, date(2026, 9, 11)),
            current_user=catalog.user,
        )

        assert pedido.scheduled_date == date(2026, 9, 11)

    def test_a_mensagem_de_erro_diz_a_data_possivel(self, monkeypatch):
        congelar(monkeypatch, datetime(2026, 9, 10, 17, 0))

        erro = InvalidScheduledDateException(date(2026, 9, 10), min_scheduled_date())

        assert "11/09/2026" in erro.message
        assert "16h" in erro.message


class TestListagemDoVendedor:
    """Sem filtro, de hoje em diante e em ordem crescente. Passado só filtrando."""

    def _listar(self, catalog, **kwargs):
        from app.orders.routes.order_routes import list_seller_orders

        params = {"search": None, "status": None, "scheduled_date": None}
        params.update(kwargs)
        return list_seller_orders(
            db=catalog.db, current_user=catalog.user, **params
        )

    def _cenario(self, catalog):
        hoje = today_sp()
        return {
            "anteontem": make_order(catalog, scheduled_date=hoje - timedelta(days=2)),
            "ontem": make_order(catalog, scheduled_date=hoje - timedelta(days=1)),
            "hoje": make_order(catalog, scheduled_date=hoje),
            "amanha": make_order(catalog, scheduled_date=hoje + timedelta(days=1)),
            "semana": make_order(catalog, scheduled_date=hoje + timedelta(days=7)),
        }

    def test_sem_filtro_esconde_o_passado(self, catalog):
        c = self._cenario(catalog)

        ids = [o.id for o in self._listar(catalog)]

        assert c["anteontem"].id not in ids
        assert c["ontem"].id not in ids

    def test_sem_filtro_traz_hoje_e_o_futuro(self, catalog):
        c = self._cenario(catalog)

        ids = [o.id for o in self._listar(catalog)]

        assert ids == [c["hoje"].id, c["amanha"].id, c["semana"].id]

    def test_ordena_da_data_mais_proxima_para_a_mais_distante(self, catalog):
        self._cenario(catalog)

        datas = [o.scheduled_date for o in self._listar(catalog)]

        assert datas == sorted(datas)
        assert datas[0] == today_sp()

    def test_filtrando_uma_data_passada_o_pedido_aparece(self, catalog):
        c = self._cenario(catalog)
        ontem = today_sp() - timedelta(days=1)

        ids = [o.id for o in self._listar(catalog, scheduled_date=ontem)]

        assert ids == [c["ontem"].id]

    def test_o_filtro_de_data_nao_traz_as_outras_datas(self, catalog):
        c = self._cenario(catalog)

        ids = [o.id for o in self._listar(catalog, scheduled_date=today_sp())]

        assert ids == [c["hoje"].id]
