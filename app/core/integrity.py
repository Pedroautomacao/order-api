"""Traduz violação de unicidade do banco para erro que o usuário entende.

Sem isto, cadastrar um cliente com CPF/CNPJ repetido virava 500 com traceback:
o usuário não descobria qual campo estava duplicado e o time recebia um erro
sem ação possível.
"""
import re

from sqlalchemy.exc import IntegrityError


# SQLSTATE de unique_violation. Usado em vez do tipo da exceção do driver para
# não amarrar em psycopg — psycopg3 expõe em `sqlstate`, psycopg2 em `pgcode`.
SQLSTATE_UNIQUE_VIOLATION = "23505"

# (tabela, coluna) -> começo da mensagem. O valor duplicado é anexado quando o
# driver o informa. token_hash fica fora de propósito: é interno e o valor é
# segredo, então cai na mensagem genérica, sem eco.
CAMPOS_UNICOS: dict[tuple[str, str], str] = {
    ("clients", "cpf_cnpj"): "Já existe um cliente com este CPF/CNPJ",
    ("products", "sku"): "Já existe um produto com este SKU",
    ("units_of_measure", "code"): "Já existe uma unidade de medida com este código",
    ("users", "username"): "Já existe um usuário com este login",
    ("users", "email"): "Já existe um usuário com este e-mail",
    ("users", "cpf"): "Já existe um usuário com este CPF",
    ("roles", "name"): "Já existe um perfil de acesso com este nome",
    ("menu_groups", "code"): "Já existe um grupo de menu com este código",
    ("permissions", "code"): "Já existe uma permissão com este código",
}

MENSAGEM_GENERICA = (
    "Já existe um registro com esse valor. Revise os campos que não podem repetir."
)

# Usado só quando o driver não informa tabela/coluna. Índice único reporta o
# nome do índice (ix_*); UniqueConstraint reporta <tabela>_<coluna>_key.
CONSTRAINTS: dict[str, tuple[str, str]] = {
    "clients_cpf_cnpj_key": ("clients", "cpf_cnpj"),
    "ix_products_sku": ("products", "sku"),
    "ix_units_of_measure_code": ("units_of_measure", "code"),
    "ix_users_username": ("users", "username"),
    "users_email_key": ("users", "email"),
    "users_cpf_key": ("users", "cpf"),
    "roles_name_key": ("roles", "name"),
    "menu_groups_code_key": ("menu_groups", "code"),
    "permissions_code_key": ("permissions", "code"),
    "ix_refresh_tokens_token_hash": ("refresh_tokens", "token_hash"),
}

# "Key (cpf_cnpj)=(123) already exists." e a tradução
# "Chave (cpf_cnpj)=(123) já existe." têm a mesma estrutura, então o regex não
# depende do lc_messages do servidor — que é pt_BR no dev e inglês na VPS.
_DETALHE = re.compile(r"\(([^()]+)\)=\((.*)\)", re.S)


def e_violacao_de_unicidade(exc: IntegrityError) -> bool:
    orig = getattr(exc, "orig", None)
    codigo = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    return codigo == SQLSTATE_UNIQUE_VIOLATION


def _resolver_campo(orig) -> tuple[str | None, str | None, str | None]:
    """(tabela, coluna, valor duplicado) do diagnóstico do driver."""
    diag = getattr(orig, "diag", None)

    tabela = getattr(diag, "table_name", None)
    coluna = None
    valor = None

    achado = _DETALHE.search(getattr(diag, "message_detail", None) or "")
    if achado:
        coluna = achado.group(1).strip()
        valor = achado.group(2).strip()

    if not (tabela and coluna):
        alvo = CONSTRAINTS.get(getattr(diag, "constraint_name", None) or "")
        if alvo:
            tabela, coluna = alvo

    return tabela, coluna, valor


def mensagem_de_unicidade(exc: IntegrityError) -> str:
    """Mensagem pronta para o usuário, com o campo que duplicou."""
    tabela, coluna, valor = _resolver_campo(getattr(exc, "orig", None))

    base = CAMPOS_UNICOS.get((tabela, coluna))
    if not base:
        return MENSAGEM_GENERICA

    return f"{base}: {valor}." if valor else f"{base}."
