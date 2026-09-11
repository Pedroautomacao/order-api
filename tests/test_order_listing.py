"""Listagem de pedidos: todos, paginados, do mais recente para o mais antigo."""
from datetime import date, timedelta

import pytest

from app.orders.enums import OrderStatus
from app.orders.routes.order_routes import list_orders

from tests.conftest import make_order

HOJE = date.today()


def listar(catalog, **kwargs):
    """Chama a rota direto, com os defaults dos Query params aplicados."""
    params = {
        "search": None,
        "status": None,
        "production_approval": None,
        "scheduled_date": None,
        "page": 1,
        "page_size": 20,
    }
    params.update(kwargs)
    return list_orders(db=catalog.db, current_user=catalog.user, **params)


@pytest.fixture()
def cinco_dias(catalog):
    """Um pedido por dia, de hoje até 4 dias atrás, criados fora de ordem."""
    pedidos = {}
    for offset in (2, 0, 4, 1, 3):
        dia = HOJE - timedelta(days=offset)
        pedidos[offset] = make_order(
            catalog, scheduled_date=dia, products=[catalog.alfa]
        )
    catalog.db.commit()
    return pedidos


class TestMostraTodos:
    def test_sem_filtro_traz_todos_os_dias(self, catalog, cinco_dias):
        """Antes a tela fixava a data em hoje e escondia o resto da base."""
        pagina = listar(catalog)

        assert pagina.total == 5
        assert len(pagina.items) == 5

    def test_ordena_do_mais_recente_para_o_mais_antigo(self, catalog, cinco_dias):
        pagina = listar(catalog)

        datas = [i.scheduled_date for i in pagina.items]
        assert datas == sorted(datas, reverse=True)
        assert datas[0] == HOJE

    def test_desempata_pelo_id_decrescente(self, catalog):
        primeiro = make_order(catalog, products=[catalog.alfa])
        segundo = make_order(catalog, products=[catalog.alfa])
        catalog.db.commit()

        pagina = listar(catalog)

        assert [i.id for i in pagina.items] == [segundo.id, primeiro.id]


class TestPaginacao:
    def test_respeita_o_tamanho_da_pagina(self, catalog, cinco_dias):
        pagina = listar(catalog, page_size=2)

        assert len(pagina.items) == 2
        assert pagina.total == 5
        assert pagina.pages == 3
        assert pagina.page == 1

    def test_segunda_pagina_continua_a_ordem(self, catalog, cinco_dias):
        primeira = listar(catalog, page=1, page_size=2)
        segunda = listar(catalog, page=2, page_size=2)

        assert segunda.items[0].scheduled_date < primeira.items[-1].scheduled_date

    def test_paginas_nao_repetem_nem_perdem_pedido(self, catalog, cinco_dias):
        vistos = []
        for numero in (1, 2, 3):
            vistos += [i.id for i in listar(catalog, page=numero, page_size=2).items]

        assert len(vistos) == 5
        assert len(set(vistos)) == 5

    def test_pagina_alem_do_fim_vem_vazia_mas_com_total(self, catalog, cinco_dias):
        pagina = listar(catalog, page=99, page_size=2)

        assert pagina.items == []
        assert pagina.total == 5

    def test_base_vazia_nao_reporta_pagina(self, catalog):
        pagina = listar(catalog)

        assert (pagina.total, pagina.pages, pagina.items) == (0, 0, [])


class TestFiltrosContinuamValendo:
    def test_por_data_de_entrega(self, catalog, cinco_dias):
        alvo = HOJE - timedelta(days=3)

        pagina = listar(catalog, scheduled_date=alvo)

        assert pagina.total == 1
        assert pagina.items[0].scheduled_date == alvo

    def test_por_status(self, catalog, cinco_dias):
        make_order(
            catalog, status=OrderStatus.BILLED, products=[catalog.alfa]
        )
        catalog.db.commit()

        pagina = listar(catalog, status=OrderStatus.BILLED.value)

        assert pagina.total == 1
        assert pagina.items[0].status == OrderStatus.BILLED.value

    def test_status_invalido_e_ignorado(self, catalog, cinco_dias):
        pagina = listar(catalog, status="NaoExiste")

        assert pagina.total == 5

    def test_por_id_do_pedido(self, catalog, cinco_dias):
        alvo = cinco_dias[0]

        pagina = listar(catalog, search=str(alvo.id))

        assert pagina.total == 1
        assert pagina.items[0].id == alvo.id

    def test_por_nome_do_cliente(self, catalog, cinco_dias):
        pagina = listar(catalog, search=catalog.client.name.lower())

        assert pagina.total == 5

    def test_filtro_reduz_o_total_e_nao_so_a_pagina(self, catalog, cinco_dias):
        """O total precisa refletir o filtro, senão a tela mostra páginas fantasma."""
        alvo = HOJE - timedelta(days=2)

        pagina = listar(catalog, scheduled_date=alvo, page_size=2)

        assert (pagina.total, pagina.pages) == (1, 1)

    def test_pedido_excluido_fica_fora(self, catalog, cinco_dias):
        cinco_dias[0].is_deleted = True
        catalog.db.commit()

        pagina = listar(catalog)

        assert pagina.total == 4
