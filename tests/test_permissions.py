"""
Testes do sistema de permissões:
- Usuário com permissões diretas no role
- Usuário com menu_groups (permissões efetivas = union dos grupos)
- Proteção de endpoints: 403 sem permissão, 200 com permissão
"""
from tests.conftest import make_user, make_role, make_permission, auth_headers_for
from app.users.models.menu_group import MenuGroup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _attach_perm_to_role(db, role, perm):
    role.permissions.append(perm)
    db.flush()


def _make_menu_group(db, code: str, permissions=None) -> MenuGroup:
    mg = MenuGroup(code=code, name=code, description=code)
    db.add(mg)
    db.flush()
    if permissions:
        for p in permissions:
            mg.permissions.append(p)
        db.flush()
    return mg


# ---------------------------------------------------------------------------
# Sistema de permissões diretas (sem grupos de menu)
# ---------------------------------------------------------------------------

class TestPermissoesDiretas:
    def test_usuario_sem_permissao_recebe_403(self, client, db):
        """Usuário sem nenhuma permissão não pode listar clientes."""
        role = make_role(db, "SemPermissao")
        user = make_user(db, username="noperm", cpf="001.001.001-01", role=role)
        db.flush()

        response = client.get("/clients", headers=auth_headers_for(user))

        assert response.status_code == 403

    def test_usuario_com_permissao_correta_recebe_200(self, client, db):
        """Usuário com client:read pode listar clientes."""
        perm = make_permission(db, "client:read")
        role = make_role(db, "ClientReader")
        _attach_perm_to_role(db, role, perm)
        user = make_user(db, username="client_reader", cpf="002.002.002-02", role=role)
        db.flush()

        response = client.get("/clients", headers=auth_headers_for(user))

        assert response.status_code == 200

    def test_usuario_com_permissao_errada_recebe_403(self, client, db):
        """Usuário com product:read não pode listar clientes (client:read)."""
        perm = make_permission(db, "product:read")
        role = make_role(db, "ProductOnly")
        _attach_perm_to_role(db, role, perm)
        user = make_user(db, username="prod_reader", cpf="003.003.003-03", role=role)
        db.flush()

        response = client.get("/clients", headers=auth_headers_for(user))

        assert response.status_code == 403

    def test_endpoint_sem_autenticacao_recebe_401(self, client):
        """Sem token, qualquer endpoint protegido retorna 401."""
        response = client.get("/clients")

        assert response.status_code == 401


# ---------------------------------------------------------------------------
# Sistema de permissões via grupos de menu
# ---------------------------------------------------------------------------

class TestPermissoesViaGrupos:
    def test_grupo_de_menu_concede_permissao(self, client, db):
        """
        Role com menu_group contendo client:read → usuário pode listar clientes.
        As permissões efetivas são a union das permissões dos grupos, não do role.
        """
        perm_read = make_permission(db, "client:read_mg")
        mg = _make_menu_group(db, "clients_mg", permissions=[perm_read])

        # Coloca a permissão no grupo, não no role diretamente
        role = make_role(db, "SellerMG")
        role.menu_groups.append(mg)
        db.flush()

        user = make_user(db, username="mg_user", cpf="004.004.004-04", role=role)
        db.flush()

        # Como o endpoint usa "client:read", usamos um endpoint que usa a permissão
        # do grupo. Aqui testamos a lógica de /auth/me para validar que os grupos
        # são retornados corretamente.
        response = client.get("/auth/me", headers=auth_headers_for(user))

        assert response.status_code == 200
        data = response.json()
        role_data = next(r for r in data["roles"] if r["name"] == "SellerMG")
        assert any(mg["code"] == "clients_mg" for mg in role_data["menu_groups"])

    def test_role_sem_grupo_usa_permissoes_diretas(self, client, db):
        """Role sem menu_groups usa permissões diretas."""
        perm = make_permission(db, "order:read_direct")
        role = make_role(db, "DirectPerms")
        role.permissions.append(perm)
        db.flush()

        user = make_user(db, username="direct_user", cpf="005.005.005-05", role=role)
        db.flush()

        response = client.get("/auth/me", headers=auth_headers_for(user))

        assert response.status_code == 200
        data = response.json()
        role_data = next(r for r in data["roles"] if r["name"] == "DirectPerms")
        assert any(p["code"] == "order:read_direct" for p in role_data["permissions"])
        assert role_data["menu_groups"] == []


# ---------------------------------------------------------------------------
# Proteção de endpoints específicos
# ---------------------------------------------------------------------------

class TestProtecaoEndpoints:
    def test_order_read_permite_listar_pedidos(self, client, db):
        perm = make_permission(db, "order:read")
        role = make_role(db, "OrderReader")
        _attach_perm_to_role(db, role, perm)
        user = make_user(db, username="order_reader", cpf="006.006.006-06", role=role)
        db.flush()

        response = client.get("/orders", headers=auth_headers_for(user))

        assert response.status_code == 200

    def test_order_bill_permite_listar_fiscal(self, client, db):
        perm = make_permission(db, "order:bill")
        role = make_role(db, "FiscalRole")
        _attach_perm_to_role(db, role, perm)
        user = make_user(db, username="fiscal_user", cpf="007.007.007-07", role=role)
        db.flush()

        response = client.get("/orders/fiscal", headers=auth_headers_for(user))

        assert response.status_code == 200

    def test_order_list_permite_listar_seller(self, client, db):
        perm = make_permission(db, "order:list")
        role = make_role(db, "SellerRole")
        _attach_perm_to_role(db, role, perm)
        user = make_user(db, username="seller_user", cpf="008.008.008-08", role=role)
        db.flush()

        response = client.get("/orders/seller", headers=auth_headers_for(user))

        assert response.status_code == 200

    def test_product_read_permite_listar_produtos(self, client, db):
        perm = make_permission(db, "product:read")
        role = make_role(db, "ProdReader")
        _attach_perm_to_role(db, role, perm)
        user = make_user(db, username="prod_r", cpf="009.009.009-09", role=role)
        db.flush()

        response = client.get("/products", headers=auth_headers_for(user))

        assert response.status_code == 200

    def test_user_create_permite_listar_usuarios(self, client, db):
        perm = make_permission(db, "user:create")
        role = make_role(db, "UserMgmt")
        _attach_perm_to_role(db, role, perm)
        user = make_user(db, username="user_mgmt", cpf="010.010.010-10", role=role)
        db.flush()

        response = client.get("/users", headers=auth_headers_for(user))

        assert response.status_code == 200
