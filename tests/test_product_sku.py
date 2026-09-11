"""SKU do produto: sempre gerado a partir do id.

Quem cadastra não escolhe o SKU — a tela não tem o campo e ele nem entra no
contrato de ProductCreate. Antes o backend o exigia no corpo e devolvia 422,
então não dava para cadastrar produto nenhum pela tela.
"""
from decimal import Decimal

from app.products.schemas.product_schema import ProductCreate
from app.products.services.product_service import ProductService


def _dados(catalog, **extra):
    payload = {
        "name": "Fraldinha",
        "unitOfMeasureId": catalog.unit.id,
        "unitPrice": Decimal("39.00"),
    }
    payload.update(extra)
    return ProductCreate(**payload)


class TestGeracaoDoSku:
    def test_o_backend_gera_o_sku_a_partir_do_id(self, catalog):
        produto = ProductService.create(
            catalog.db, data=_dados(catalog), current_user=catalog.user
        )

        assert produto.sku == str(produto.id)

    def test_nao_sobra_placeholder_temporario(self, catalog):
        produto = ProductService.create(
            catalog.db, data=_dados(catalog), current_user=catalog.user
        )
        catalog.db.refresh(produto)

        assert not produto.sku.startswith("tmp-")

    def test_sku_enviado_pelo_cliente_e_ignorado(self, catalog):
        """Não existe caminho para escolher o SKU, nem mandando no corpo.

        O campo não está em ProductCreate, então o pydantic descarta e o
        backend gera do mesmo jeito.
        """
        produto = ProductService.create(
            catalog.db, data=_dados(catalog, sku="ESCOLHIDO"), current_user=catalog.user
        )

        assert produto.sku == str(produto.id)

    def test_sku_nao_faz_parte_do_contrato_de_entrada(self, catalog):
        assert "sku" not in ProductCreate.model_fields

    def test_dois_produtos_seguidos_nao_colidem(self, catalog):
        um = ProductService.create(
            catalog.db, data=_dados(catalog, name="Um"), current_user=catalog.user
        )
        dois = ProductService.create(
            catalog.db, data=_dados(catalog, name="Dois"), current_user=catalog.user
        )

        assert um.sku != dois.sku
