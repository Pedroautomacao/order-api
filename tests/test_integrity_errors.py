"""Violação de unicidade traduzida para mensagem de usuário.

Os diagnósticos são montados à mão: o que importa é o que o driver entrega ao
handler, e reproduzir cada constraint exigiria um Postgres por caso.
"""
import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.integrity import (
    MENSAGEM_GENERICA,
    e_violacao_de_unicidade,
    mensagem_de_unicidade,
)
from app.main import integrity_error_handler


class _ErroDoDriver(Exception):
    """Erro do psycopg como o SQLAlchemy o embrulha em `orig`."""

    def __init__(self, sqlstate, diag):
        self.sqlstate = sqlstate
        self.diag = diag


def _erro(
    *,
    sqlstate="23505",
    table_name=None,
    constraint_name=None,
    message_detail=None,
):
    """IntegrityError de verdade, com o diagnóstico que o driver entregaria."""
    diag = SimpleNamespace(
        table_name=table_name,
        constraint_name=constraint_name,
        message_detail=message_detail,
    )
    return IntegrityError(
        "INSERT INTO ...", {}, _ErroDoDriver(sqlstate, diag)
    )


class TestReconhecimento:
    def test_unique_violation_e_reconhecida(self):
        assert e_violacao_de_unicidade(_erro()) is True

    @pytest.mark.parametrize(
        "sqlstate",
        [
            "23503",  # foreign_key_violation
            "23502",  # not_null_violation
            "23514",  # check_violation
        ],
    )
    def test_outras_violacoes_nao_sao(self, sqlstate):
        assert e_violacao_de_unicidade(_erro(sqlstate=sqlstate)) is False

    def test_psycopg2_usa_pgcode(self):
        class ErroPsycopg2(Exception):
            pgcode = "23505"
            diag = SimpleNamespace(
                table_name=None, constraint_name=None, message_detail=None
            )

        exc = IntegrityError("INSERT INTO ...", {}, ErroPsycopg2())
        assert e_violacao_de_unicidade(exc) is True


class TestMensagem:
    def test_caso_real_do_cliente(self):
        """O erro que chegou de produção, com o DETAIL em inglês."""
        exc = _erro(
            table_name="clients",
            constraint_name="clients_cpf_cnpj_key",
            message_detail="Key (cpf_cnpj)=(12343455535) already exists.",
        )

        assert (
            mensagem_de_unicidade(exc)
            == "Já existe um cliente com este CPF/CNPJ: 12343455535."
        )

    def test_servidor_com_mensagens_em_portugues(self):
        """O Postgres de dev roda com lc_messages pt_BR; a estrutura é a mesma."""
        exc = _erro(
            table_name="clients",
            constraint_name="clients_cpf_cnpj_key",
            message_detail="Chave (cpf_cnpj)=(12343455535) já existe.",
        )

        assert (
            mensagem_de_unicidade(exc)
            == "Já existe um cliente com este CPF/CNPJ: 12343455535."
        )

    @pytest.mark.parametrize(
        "tabela,coluna,esperado",
        [
            ("products", "sku", "Já existe um produto com este SKU"),
            ("units_of_measure", "code", "Já existe uma unidade de medida com este código"),
            ("users", "username", "Já existe um usuário com este login"),
            ("users", "email", "Já existe um usuário com este e-mail"),
            ("users", "cpf", "Já existe um usuário com este CPF"),
            ("roles", "name", "Já existe um perfil de acesso com este nome"),
        ],
    )
    def test_cada_campo_unico_tem_mensagem(self, tabela, coluna, esperado):
        exc = _erro(
            table_name=tabela,
            message_detail=f"Key ({coluna})=(abc) already exists.",
        )

        assert mensagem_de_unicidade(exc) == f"{esperado}: abc."

    def test_sem_o_valor_a_frase_continua_fechando(self):
        exc = _erro(table_name="clients", constraint_name="clients_cpf_cnpj_key")

        assert mensagem_de_unicidade(exc) == "Já existe um cliente com este CPF/CNPJ."

    def test_cai_no_nome_da_constraint_quando_falta_diagnostico(self):
        """Sem table_name nem DETAIL, o nome da constraint ainda identifica."""
        exc = _erro(constraint_name="ix_products_sku")

        assert mensagem_de_unicidade(exc) == "Já existe um produto com este SKU."

    def test_constraint_desconhecida_usa_a_generica(self):
        exc = _erro(table_name="alguma_tabela", constraint_name="alguma_coisa_key")

        assert mensagem_de_unicidade(exc) == MENSAGEM_GENERICA

    def test_token_de_refresh_nao_ecoa_o_valor(self):
        """token_hash é segredo: fica fora do mapa e não aparece na resposta."""
        exc = _erro(
            table_name="refresh_tokens",
            constraint_name="ix_refresh_tokens_token_hash",
            message_detail="Key (token_hash)=(ab12cd34segredo) already exists.",
        )

        mensagem = mensagem_de_unicidade(exc)

        assert mensagem == MENSAGEM_GENERICA
        assert "ab12cd34segredo" not in mensagem


class TestHandler:
    """O contrato que o frontend consome: status e a chave `detail`."""

    def _responder(self, exc):
        pedido = SimpleNamespace(url=SimpleNamespace(path="/clients"))
        return asyncio.run(integrity_error_handler(pedido, exc))

    def test_unicidade_vira_409_com_detail(self):
        resposta = self._responder(
            _erro(
                table_name="clients",
                constraint_name="clients_cpf_cnpj_key",
                message_detail="Key (cpf_cnpj)=(12343455535) already exists.",
            )
        )

        assert resposta.status_code == 409
        # `detail` é a chave que o api.ts do front lê para montar o popup
        assert b'"detail"' in resposta.body
        assert "12343455535" in resposta.body.decode()

    def test_chave_estrangeira_continua_subindo(self):
        """FK é defeito de código: tem de seguir como 500, não virar 409."""
        with pytest.raises(IntegrityError):
            self._responder(_erro(sqlstate="23503"))
