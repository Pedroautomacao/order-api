"""Tradução de erro de regra de negócio para HTTP.

Sem o handler global qualquer DomainException que a rota não capturasse virava
500 — era o caso de finalizar um pedido com item ainda pendente.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.clients.exception_handler import ClientNotFoundException
from app.core.exceptions import DomainException
from app.main import app as real_app, domain_exception_handler
from app.orders.exception_handler import (
    CreditLimitExceededException,
    DuplicateOrderForClientException,
    NoOrderAvailableException,
    OrderItemNotFoundException,
    OrderNotFinishedException,
    OrderNotFoundException,
    WorkItemNotFoundException,
)
from app.products.exception_handler import (
    ProductNotFoundException,
    UnitOfMeasureNotFoundException,
)
from app.units.exception_handler import UnitNotFoundException


@pytest.fixture()
def client():
    """App mínima com o handler real, sem autenticação no caminho."""
    app = FastAPI()
    app.add_exception_handler(DomainException, domain_exception_handler)

    @app.get("/nao-encontrado")
    def nao_encontrado():
        raise OrderNotFoundException(42)

    @app.get("/regra-de-negocio")
    def regra_de_negocio():
        raise OrderNotFinishedException()

    return TestClient(app)


class TestHandlerRegistrado:
    def test_app_real_registra_o_handler(self):
        assert DomainException in real_app.exception_handlers


class TestRespostaHttp:
    def test_nao_encontrado_responde_404(self, client):
        resposta = client.get("/nao-encontrado")

        assert resposta.status_code == 404

    def test_regra_de_negocio_responde_400(self, client):
        resposta = client.get("/regra-de-negocio")

        assert resposta.status_code == 400

    def test_corpo_usa_detail_como_o_httpexception(self, client):
        """O front lê `error.detail`; o formato precisa ser o mesmo."""
        resposta = client.get("/regra-de-negocio")

        assert resposta.json() == {
            "detail": "Ainda há itens não produzidos neste pedido."
        }


class TestStatusPorExcecao:
    @pytest.mark.parametrize(
        "excecao",
        [
            ClientNotFoundException(1),
            ProductNotFoundException(1),
            UnitOfMeasureNotFoundException(1),
            UnitNotFoundException(1),
            OrderNotFoundException(1),
            OrderItemNotFoundException(1),
            WorkItemNotFoundException(),
            NoOrderAvailableException(),
        ],
    )
    def test_nao_encontrado(self, excecao):
        assert excecao.status_code == 404

    @pytest.mark.parametrize(
        "excecao",
        [
            OrderNotFinishedException(),
            DuplicateOrderForClientException(),
            CreditLimitExceededException(limit=10, outstanding=5, order_amount=20),
        ],
    )
    def test_regra_de_negocio(self, excecao):
        assert excecao.status_code == 400

    def test_padrao_da_base_e_400(self):
        assert DomainException.status_code == 400
