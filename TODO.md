# TODO geral – Order (API + Web)

Visão do projeto Order Management System: backend (order-api) e frontend (order-web).

---

## Concluído

- [x] **Permissões por grupos de menu** – Backend e front calculam permissões efetivas a partir dos grupos do perfil; `/auth/me` retorna grupos com `permissions`; front usa só grupos quando existirem.
- [x] **Usuário só fiscal** – Sem loop 403: endpoints `GET /orders/fiscal` e `GET /orders/fiscal/:id` com `order:bill`; tela Fiscal usa esses endpoints; menu lateral não mostra itens até carregar permissões.
- [x] **Edição de grupos de menu** – `PUT /menu-groups/:id`; listagem de grupos com permissões; na web: botão Editar e modal para nome, descrição e permissões (código não editável).
- [x] **Validação ao criar/editar usuário** – Verificação de username, e-mail e CPF duplicados; mensagens 400 claras; no update, e-mail não pode ser de outro usuário.
- [x] **Permissões tech ocultas** – `GET /users/permissions` não retorna códigos `tech` / `tech:*`; não aparecem na UI ao editar grupos ou perfis.
- [x] **Cache em /auth/me** – Header `Cache-Control: no-store` para evitar cache de permissões no navegador.
- [x] **Dashboard snapshot job** – Payload do snapshot convertido para JSON serializável (Decimal → float, datetime → isoformat).
- [x] **Tela de vendedor** – Endpoints `/orders/seller` (list, detail, update, cancel); tela "Meus Pedidos" com criar/editar/cancelar pedidos; rota protegida por `order:list`; vendedor não tem mais `order:read`.
- [x] **Tela de produtor** – Endpoints `assign_next`, `finish`, `confirm_item`, `update_item_quantity`; permissão `order:produce`; tela com 3 estados (idle / producing / review); item a item com edição antes de finalizar.
- [x] **Criar pedido pelo admin** – Botão "Criar Pedido" na tela de Pedidos (admin); modal com seleção de cliente, data de entrega e itens; sem menu separado.
- [x] **Validação de data na criação de pedido** – Não permite data no passado; após 16h (BRT) só permite a partir de amanhã.
- [x] **SKUs únicos por pedido** – Impede produtos duplicados no formulário de criação; remove do dropdown itens já selecionados em outras linhas.
- [x] **Responsividade geral** – Drawer 0px no mobile; filtros empilham no mobile; DataGrid sem minWidth 600 forçado; campo de busca responsivo; hamburger oculto no desktop.
- [x] **Tela de auditoria** – Listagem de logs com filtros (ação, entidade, usuário, data); busca ao alterar filtros (sem botão Filtrar); menu e rota protegida por `audit:read`.
- [x] **Migrations de roles/permissões** – Nomes corretos dos perfis no BD (`Admin`, `Vendedor`, `Produtor`); grupos `seller`, `producer`, `orders`, `clients`, `products` com permissões adequadas.
- [x] **Filtro por data de entrega** – Filtro `scheduled_date` adicionado nos endpoints e UI de Pedidos, Meus Pedidos e Fiscal; padrão = hoje; busca por nome/CPF/CNPJ/ID.
- [x] **Proteção de rotas no front** – Todas as rotas admin agora têm `RequirePermissionOrRedirect`: products, clients, orders, fiscal, users. `PrivateRoute` bloqueia renderização durante loading.
- [x] **Mensagens de erro normalizadas** – `api.ts` converte erros de validação Pydantic (array) para string legível; erros 403 e 400 exibem `detail` corretamente.
- [x] **Testes automatizados (API)** – Infraestrutura pytest com `conftest.py`, transações revertidas, TestClient; `test_auth.py` (login, /auth/me); `test_permissions.py` (permissões diretas, grupos, endpoints).
- [x] **Documentação de permissões** – `PERMISSIONS.md` com tabela de permissões, perfis padrão, mapa rota→permissão e guia para adicionar novas permissões.

---

## Em andamento

_(nada no momento)_

---

## Backlog / ideias

- Exportação de relatórios (pedidos, faturamento).
- Notificações ou avisos para pedidos próximos do vencimento.
- Paginação server-side nas listagens (hoje carrega tudo de uma vez).
- Reset de senha por admin.

---

_Última atualização: mar/2026_
