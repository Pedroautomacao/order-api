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

---

## Em andamento

_(nada no momento)_

---

## A desenvolver

- [ ] **Tela de vendedor** – Funcionalidades e UI para perfil vendedor (API + Web).
- [ ] **Tela de produtor** – Funcionalidades e UI para perfil produtor (API + Web).
- [x] **Tela de auditoria** – Listagem de logs com filtros (ação, entidade, usuário, data); busca ao alterar filtros (sem botão Filtrar); menu e rota protegida por `audit:read`.

---

## Próximos passos (sugestão)

- [ ] Testes automatizados (API: endpoints de auth/permissões; Web: fluxos críticos).
- [ ] Documentar regras de permissão (tech, admin, grupos de menu) para onboarding.
- [ ] Revisar proteção de rotas no front (RequirePermissionOrRedirect em todas as rotas admin que precisem).
- [ ] Melhorar mensagens de erro no front (ex.: exibir `detail` da API em 400/403).

---

## Backlog / ideias

- Filtros e busca nas listagens (pedidos, clientes, produtos) já existentes.
- Exportação de relatórios (pedidos, faturamento).
- Notificações ou avisos para pedidos próximos do vencimento.

---

_Última atualização: fev/2026_
