"""Romaneio de produção em PDF."""
from datetime import timedelta

import pytest

from app.core.time import today_sp
from app.orders.enums import OrderStatus
from app.orders.services.order_pdf_service import OrderPdfService

from tests.conftest import make_order


def _listar(catalog, quando=None):
    return OrderPdfService.listar_pedidos(
        catalog.db, scheduled_date=quando or today_sp()
    )


def _gerar(catalog, quando=None):
    return OrderPdfService.build(catalog.db, scheduled_date=quando or today_sp())


class TestQuaisPedidosEntram:
    @pytest.mark.parametrize(
        "status", [OrderStatus.AWAITING, OrderStatus.PRODUCING, OrderStatus.PRODUCED]
    )
    def test_pendente_em_producao_e_produzido_entram(self, catalog, status):
        pedido = make_order(catalog, status=status)

        assert pedido.id in [o.id for o in _listar(catalog)]

    @pytest.mark.parametrize("status", [OrderStatus.BILLED, OrderStatus.CANCELED])
    def test_faturado_e_cancelado_ficam_de_fora(self, catalog, status):
        pedido = make_order(catalog, status=status)

        assert pedido.id not in [o.id for o in _listar(catalog)]

    def test_filtra_pela_data_de_entrega(self, catalog):
        hoje = make_order(catalog)
        amanha = make_order(catalog, scheduled_date=today_sp() + timedelta(days=1))

        ids = [o.id for o in _listar(catalog)]

        assert ids == [hoje.id]
        assert amanha.id not in ids


class TestOrdem:
    def test_prioridade_primeiro_depois_id(self, catalog):
        """Mesma ordem da fila do produtor: o maço sai na ordem de produção."""
        b1 = make_order(catalog)
        b1.priority = "B"
        a1 = make_order(catalog)
        a1.priority = "A"
        a2 = make_order(catalog)
        a2.priority = "A"
        catalog.db.flush()

        assert [o.id for o in _listar(catalog)] == [a1.id, a2.id, b1.id]


class TestArquivoGerado:
    def test_sai_um_pdf_valido(self, catalog):
        make_order(catalog)

        conteudo = _gerar(catalog)

        assert conteudo.startswith(b"%PDF-")
        assert conteudo.rstrip().endswith(b"%%EOF")

    def test_sem_pedido_ainda_gera_o_arquivo(self, catalog):
        """Data vazia não pode estourar: o gestor pode escolher qualquer dia."""
        assert _gerar(catalog, quando=today_sp() + timedelta(days=90)).startswith(b"%PDF-")

    def test_nao_sobra_o_marcador_de_total_de_paginas(self, catalog):
        """O {nb} do rodapé tem de virar número no fechamento do documento."""
        make_order(catalog)

        assert b"{nb}" not in _gerar(catalog)

    def test_nome_com_acento_nao_derruba_a_geracao(self, catalog):
        """Fonte core é latin-1 e nome de produto vem digitado por gente."""
        catalog.alfa.name = "Coração à açafrão"
        catalog.db.flush()
        make_order(catalog, products=[catalog.alfa])

        assert _gerar(catalog).startswith(b"%PDF-")
