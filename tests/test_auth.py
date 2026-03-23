"""
Testes do módulo de autenticação: POST /auth/login e GET /auth/me.
"""
from tests.conftest import make_user, make_role, auth_headers_for


class TestLogin:
    def test_login_sucesso(self, client, db):
        make_user(db, username="admin_test", password="senha123", cpf="111.111.111-11")
        db.flush()

        response = client.post("/auth/login", json={"username": "admin_test", "password": "senha123"})

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert isinstance(data["access_token"], str)
        assert len(data["access_token"]) > 20

    def test_login_credenciais_invalidas(self, client, db):
        make_user(db, username="real_user", password="correta", cpf="222.222.222-22")
        db.flush()

        response = client.post("/auth/login", json={"username": "real_user", "password": "errada"})

        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid credentials"

    def test_login_usuario_inexistente(self, client):
        response = client.post("/auth/login", json={"username": "naoexiste", "password": "qualquer"})

        assert response.status_code == 401

    def test_login_usuario_inativo(self, client, db):
        user = make_user(db, username="inativo", password="senha", cpf="333.333.333-33")
        user.is_active = False
        db.flush()

        response = client.post("/auth/login", json={"username": "inativo", "password": "senha"})

        assert response.status_code == 401

    def test_login_campos_obrigatorios(self, client):
        response = client.post("/auth/login", json={})

        assert response.status_code == 422


class TestGetMe:
    def test_me_autenticado(self, client, db):
        user = make_user(db, username="me_user", cpf="444.444.444-44")
        db.flush()

        response = client.get("/auth/me", headers=auth_headers_for(user))

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user.id
        assert data["username"] == "me_user"

    def test_me_sem_token(self, client):
        response = client.get("/auth/me")

        assert response.status_code == 401

    def test_me_token_invalido(self, client):
        response = client.get("/auth/me", headers={"Authorization": "Bearer token_invalido"})

        assert response.status_code == 401

    def test_me_retorna_roles(self, client, db):
        role = make_role(db, "TestRole")
        user = make_user(db, username="user_com_role", cpf="555.555.555-55", role=role)
        db.flush()

        response = client.get("/auth/me", headers=auth_headers_for(user))

        assert response.status_code == 200
        data = response.json()
        assert any(r["name"] == "TestRole" for r in data["roles"])

    def test_me_header_no_cache(self, client, db):
        user = make_user(db, username="cache_user", cpf="666.666.666-66")
        db.flush()

        response = client.get("/auth/me", headers=auth_headers_for(user))

        assert "no-store" in response.headers.get("cache-control", "")
