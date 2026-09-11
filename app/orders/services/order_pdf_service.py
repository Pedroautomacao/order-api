"""Romaneio de produção em PDF.

Existe para o dia em que o estabelecimento fica sem internet: o gestor puxa o
PDF por um celular, imprime, e a produção roda no papel. Por isso o papel é a
autorização — a liberação de produção não filtra nada aqui, quem decide o que
vai para a produção é quem separa as folhas.
"""
from datetime import date
from decimal import Decimal
from pathlib import Path

from fpdf import FPDF
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.time import now_sp
from app.orders.enums import OrderStatus
from app.orders.models.order import Order
from app.orders.models.order_item import OrderItem
from app.products.models.product import Product

LOGO_PADRAO = Path(__file__).resolve().parents[2] / "assets" / "logo.png"

# A4 retrato, em mm
MARGEM = 15.0
LARGURA_UTIL = 180.0
TOPO_CONTEUDO = 34.0
LIMITE_INFERIOR = 272.0

ALTURA_LINHA = 10.0
ALTURA_BLOCO_PEDIDO = 32.0
ALTURA_CABECALHO_TABELA = 8.0
ALTURA_FECHO = 20.0
ALTURA_TARJA = 10.0

# soma 180
COLUNAS = [
    ("#", 10.0, "C"),
    ("Produto", 66.0, "L"),
    ("Valor unit.", 24.0, "R"),
    ("Qtd.", 24.0, "R"),
    ("Total", 26.0, "R"),
    ("QTD. REAL", 30.0, "C"),
]


def _txt(valor) -> str:
    """Texto seguro para as fontes core do PDF, que são latin-1.

    Caractere fora do latin-1 (travessão, aspa curva) derruba a geração, e
    nome de produto vem digitado por gente.
    """
    texto = "" if valor is None else str(valor)
    return texto.encode("latin-1", "replace").decode("latin-1")


def _moeda(valor) -> str:
    numero = Decimal(str(valor or 0)).quantize(Decimal("0.01"))
    inteiro, centavos = f"{numero:.2f}".split(".")
    milhar = f"{int(inteiro):,}".replace(",", ".")
    return f"{milhar},{centavos}"


def _quantidade(valor, unidade=None) -> str:
    if valor is None:
        return "-"
    numero = float(valor)
    texto = f"{numero:.3f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{texto} {unidade}" if unidade else texto


class _Romaneio(FPDF):
    def __init__(self, entrega: date):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.entrega = entrega
        self.emitido_em = now_sp()
        # Definida antes de cada add_page(). Desenhada no header() de propósito:
        # assim ela sai por baixo do conteúdo, sem atrapalhar a leitura.
        self.marca_dagua: str | None = None
        self.set_auto_page_break(auto=False)
        self.set_margins(MARGEM, MARGEM, MARGEM)
        self.set_title(_txt(f"Pedidos {entrega.strftime('%d-%m-%Y')}"))

        logo = settings.brand_logo_path or str(LOGO_PADRAO)
        self.logo = logo if Path(logo).is_file() else None

    def header(self):
        if self.logo:
            self.image(self.logo, x=MARGEM, y=10, w=12, h=12)

        self.set_xy(MARGEM + (16 if self.logo else 0), 11)
        self.set_font("Helvetica", "B", 14)
        self.cell(90, 6, _txt(settings.brand_name.upper()))

        self.set_xy(MARGEM + (16 if self.logo else 0), 17)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(110)
        self.cell(90, 5, _txt(settings.brand_tagline))
        self.set_text_color(0)

        self.set_font("Helvetica", "B", 10)
        self.set_xy(MARGEM + 110, 11)
        self.cell(70, 6, _txt(f"Entrega: {self.entrega.strftime('%d/%m/%Y')}"), align="R")

        self.set_font("Helvetica", "", 8)
        self.set_text_color(110)
        self.set_xy(MARGEM + 110, 17)
        self.cell(
            70,
            5,
            _txt(f"Emitido em {self.emitido_em.strftime('%d/%m/%Y %H:%M')}"),
            align="R",
        )
        self.set_text_color(0)

        self.set_draw_color(180)
        self.line(MARGEM, 28, MARGEM + LARGURA_UTIL, 28)
        self.set_draw_color(0)

        self._desenhar_marca_dagua()

    def _desenhar_marca_dagua(self):
        if not self.marca_dagua:
            return
        self.set_font("Helvetica", "B", 34)
        self.set_text_color(214, 160, 140)
        with self.rotation(30, x=105, y=150):
            self.set_xy(0, 140)
            self.cell(210, 20, _txt(self.marca_dagua), align="C")
        self.set_text_color(0)

    def footer(self):
        self.set_y(-16)
        self.set_draw_color(180)
        self.line(MARGEM, self.get_y(), MARGEM + LARGURA_UTIL, self.get_y())
        self.set_draw_color(0)

        self.set_y(-13)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(110)
        self.cell(90, 5, _txt(settings.brand_name))
        # {nb} é substituído pelo total de páginas no fechamento do documento
        self.cell(90, 5, _txt(f"Página {self.page_no()} de {{nb}}"), align="R")
        self.set_text_color(0)

    # ----- blocos da página -------------------------------------------------

    def bloco_do_pedido(self, order: Order) -> None:
        self.set_xy(MARGEM, TOPO_CONTEUDO)
        self.set_font("Helvetica", "B", 16)
        self.cell(120, 8, _txt(f"PEDIDO #{order.id}"))

        self.set_font("Helvetica", "B", 11)
        self.cell(60, 8, _txt(f"Prioridade {order.priority or '-'}"), align="R")

        pago = "Pago" if order.is_paid else "Pendente"
        forma = "A prazo" if str(order.payment_method).endswith("CREDIT") else "À vista"
        cliente = order.client.name if order.client else "-"
        autor = "-"
        if order.created_by:
            autor = order.created_by.full_name or order.created_by.username

        linhas = [
            ("Cliente", f"{cliente} (#{order.client_id})", "Pagamento", forma),
            ("Criado por", autor, "Situação", pago),
            ("Entrega", order.scheduled_date.strftime("%d/%m/%Y"), "Total", f"R$ {_moeda(order.total_amount)}"),
        ]

        y = TOPO_CONTEUDO + 10
        for rotulo_a, valor_a, rotulo_b, valor_b in linhas:
            self.set_xy(MARGEM, y)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(110)
            self.cell(22, 5, _txt(rotulo_a))
            self.set_text_color(0)
            self.set_font("Helvetica", "B", 10)
            self.cell(76, 5, _txt(valor_a))

            self.set_font("Helvetica", "", 8)
            self.set_text_color(110)
            self.cell(22, 5, _txt(rotulo_b))
            self.set_text_color(0)
            self.set_font("Helvetica", "B", 10)
            self.cell(60, 5, _txt(valor_b))
            y += 6

        self.set_y(TOPO_CONTEUDO + ALTURA_BLOCO_PEDIDO)

    def tarja_de_continuacao(self, order: Order) -> None:
        """Identifica a folha quando o pedido não coube numa página só."""
        cliente = order.client.name if order.client else "-"
        self.set_xy(MARGEM, TOPO_CONTEUDO)
        self.set_font("Helvetica", "B", 11)
        self.cell(120, 6, _txt(f"PEDIDO #{order.id} - {cliente}"))
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(110)
        self.cell(60, 6, _txt("(continuação)"), align="R")
        self.set_text_color(0)
        self.set_y(TOPO_CONTEUDO + ALTURA_TARJA)

    def cabecalho_da_tabela(self) -> None:
        self.set_x(MARGEM)
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(235)
        for titulo, largura, alinhamento in COLUNAS:
            self.cell(largura, ALTURA_CABECALHO_TABELA, _txt(titulo), border=1,
                      align=alinhamento, fill=True)
        self.set_y(self.get_y() + ALTURA_CABECALHO_TABELA)

    def linha_do_item(self, indice: int, item: OrderItem, qtd_real: str = "") -> None:
        produto = item.product
        unidade = None
        if produto is not None and produto.unit_of_measure is not None:
            unidade = produto.unit_of_measure.code

        y = self.get_y()
        self.set_xy(MARGEM, y)

        valores = [
            str(indice),
            None,  # produto desenhado à parte: nome + SKU em duas linhas
            f"R$ {_moeda(item.unit_price)}",
            _quantidade(item.quantity, unidade),
            f"R$ {_moeda(item.total_price)}",
            # em branco o produtor anota à caneta; no pedido já produzido vem
            # preenchido com o que ele registrou no sistema
            qtd_real,
        ]

        x = MARGEM
        for (_, largura, alinhamento), valor in zip(COLUNAS, valores):
            self.set_xy(x, y)
            self.set_font("Helvetica", "", 9)
            if valor is None:
                self.cell(largura, ALTURA_LINHA, "", border=1)
                self.set_xy(x + 1.5, y + 1)
                self.set_font("Helvetica", "B", 9)
                self.cell(largura - 3, 4.5, _txt(produto.name if produto else "-"))
                self.set_xy(x + 1.5, y + 5)
                self.set_font("Helvetica", "", 7)
                self.set_text_color(110)
                self.cell(largura - 3, 4, _txt(f"SKU {produto.sku}" if produto else ""))
                self.set_text_color(0)
            else:
                self.cell(largura, ALTURA_LINHA, _txt(valor), border=1, align=alinhamento)
            x += largura

        self.set_y(y + ALTURA_LINHA)

    def fecho_do_pedido(self, order: Order) -> None:
        y = self.get_y()
        self.set_xy(MARGEM, y)
        self.set_font("Helvetica", "B", 11)
        self.cell(LARGURA_UTIL, 8,
                  _txt(f"TOTAL DO PEDIDO   R$ {_moeda(order.total_amount)}"), align="R")

        self.set_xy(MARGEM, y + 12)
        self.set_font("Helvetica", "", 9)
        self.cell(110, 6, _txt("Conferido por: _________________________________"))
        self.cell(70, 6, _txt("Data: ____/____/________"), align="R")
        self.set_y(y + ALTURA_FECHO)

    def espaco_restante(self) -> float:
        return LIMITE_INFERIOR - self.get_y()


class OrderPdfService:
    """Monta o romaneio dos pedidos de uma data de entrega."""

    # Faturado já passou pelo fiscal, e cancelado não deve ser produzido nem
    # faturado. O resto entra: Aguardando e Em produção para o produtor,
    # Produzido para chegar ao fiscal — a internet pode cair antes disso.
    STATUS_FORA = (OrderStatus.BILLED, OrderStatus.CANCELED)

    AVISO_FISCAL = "ENCAMINHAR PARA O FISCAL"

    @staticmethod
    def listar_pedidos(db: Session, *, scheduled_date: date) -> list[Order]:
        return (
            db.query(Order)
            .filter(
                Order.scheduled_date == scheduled_date,
                Order.status.notin_(OrderPdfService.STATUS_FORA),
                Order.is_deleted.is_(False),
            )
            .options(
                joinedload(Order.client),
                joinedload(Order.created_by),
                joinedload(Order.items)
                .joinedload(OrderItem.product)
                .joinedload(Product.unit_of_measure),
            )
            # mesma ordem da fila do produtor: prioridade A primeiro, depois o
            # mais antigo. O maço sai na ordem em que será produzido.
            .order_by(Order.priority.asc(), Order.id.asc())
            .all()
        )

    @staticmethod
    def build(db: Session, *, scheduled_date: date) -> bytes:
        pedidos = OrderPdfService.listar_pedidos(db, scheduled_date=scheduled_date)

        pdf = _Romaneio(scheduled_date)
        pdf.alias_nb_pages()

        if not pedidos:
            pdf.add_page()
            pdf.set_xy(MARGEM, TOPO_CONTEUDO + 20)
            pdf.set_font("Helvetica", "", 12)
            pdf.cell(
                LARGURA_UTIL,
                10,
                _txt("Nenhum pedido pendente de produção para esta data."),
                align="C",
            )
            return bytes(pdf.output())

        for pedido in pedidos:
            # Pedido já produzido não vai para a produção: vai para o fiscal
            # faturar, e a marca d'água é o que diz isso a quem separa o maço.
            produzido = pedido.status == OrderStatus.PRODUCED
            pdf.marca_dagua = OrderPdfService.AVISO_FISCAL if produzido else None

            # cada pedido começa em folha nova: papel de um pedido nunca se
            # mistura com o de outro
            pdf.add_page()
            pdf.bloco_do_pedido(pedido)
            pdf.cabecalho_da_tabela()

            itens = sorted(
                pedido.items or [],
                key=lambda i: ((i.product.name if i.product else "").lower()),
            )

            for indice, item in enumerate(itens, start=1):
                # a linha só entra se o que sobra ainda comportar o fecho; caso
                # contrário o fecho ficaria órfão no topo da folha seguinte
                if pdf.espaco_restante() < ALTURA_LINHA:
                    pdf.add_page()
                    pdf.tarja_de_continuacao(pedido)
                    pdf.cabecalho_da_tabela()

                unidade = None
                if item.product is not None and item.product.unit_of_measure is not None:
                    unidade = item.product.unit_of_measure.code
                real = (
                    _quantidade(item.produced_quantity, unidade)
                    if produzido and item.produced_quantity is not None
                    else ""
                )
                pdf.linha_do_item(indice, item, qtd_real=real)

            if pdf.espaco_restante() < ALTURA_FECHO:
                pdf.add_page()
                pdf.tarja_de_continuacao(pedido)
            pdf.fecho_do_pedido(pedido)

        return bytes(pdf.output())
