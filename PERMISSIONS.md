# Sistema de Permissões — Order API

## Visão Geral

O sistema usa **roles** (perfis) atribuídos a usuários. Cada role pode ter:
- **Permissões diretas** (`role.permissions`), ou
- **Grupos de menu** (`role.menu_groups`), cada um com suas próprias permissões.

A regra é: **se o role tem pelo menos um grupo de menu, as permissões efetivas são a união das permissões de todos os grupos**. As permissões diretas do role são ignoradas. Se não há grupos, usam-se as permissões diretas.

```
Permissões efetivas =
  SE role.menu_groups não vazio:
    union(group.permissions for group in role.menu_groups)
  SENÃO:
    role.permissions
```

Essa lógica está implementada em:
- **Backend**: `app/users/services/permission_service.py` → `get_user_permissions()`
- **Frontend**: `hooks/useAuth/index.tsx` → `refreshUserPermissions()`

---

## Permissões Existentes

| Código                  | Descrição                                      |
|-------------------------|------------------------------------------------|
| `dashboard:read`        | Acessar o dashboard                            |
| `order:read`            | Listar e ver todos os pedidos (admin)          |
| `order:create`          | Criar pedidos                                  |
| `order:list`            | Listar e ver pedidos próprios (vendedor)        |
| `order:produce`         | Produzir pedidos (tela de produtor)            |
| `order:bill`            | Faturar pedidos (tela fiscal)                  |
| `order:cancel`          | Cancelar pedidos (admin)                       |
| `order:reset_production`| Resetar produção de pedido                     |
| `client:read`           | Listar e ver clientes                          |
| `client:create`         | Criar clientes                                 |
| `client:update`         | Editar clientes                                |
| `client:delete`         | Deletar clientes                               |
| `product:read`          | Listar e ver produtos                          |
| `product:create`        | Criar produtos                                 |
| `product:update`        | Editar produtos                                |
| `product:delete`        | Deletar produtos                               |
| `unit:list`             | Listar unidades de medida                      |
| `unit:create`           | Criar unidades de medida                       |
| `unit:update`           | Editar unidades de medida                      |
| `unit:delete`           | Deletar unidades de medida                     |
| `user:create`           | Criar e gerenciar usuários                     |
| `audit:read`            | Ver logs de auditoria                          |
| `tech:*`                | Permissões internas (não exibidas na UI)       |

---

## Perfis Padrão (Roles no BD)

### Admin
- Acesso via grupo de menu `orders` (order:read, order:create, order:cancel, order:bill)
- Acesso via grupo de menu `clients` (client:read, client:create, client:update, client:delete)
- Acesso via grupo de menu `products` (product:read, product:create, product:update, product:delete, unit:*)
- Acesso via grupo de menu `producer` (order:produce)
- Permissões adicionais diretas: `dashboard:read`, `user:create`, `audit:read`

### Vendedor (`Vendedor`)
- Grupo de menu: `seller`
  - `order:list` — listar e criar seus próprios pedidos
  - `order:create` — necessário para carregar clientes/produtos no formulário

### Produtor (`Produtor`)
- Grupo de menu: `producer`
  - `order:produce` — pegar próximo pedido, confirmar itens, finalizar

### Fiscal (`Fiscal`)
- Grupo de menu: `orders` (subconjunto)
  - `order:bill` — ver pedidos produzidos e faturar

### Tech (`Tech`)
- Permissões `tech:*` — acesso total, ignora verificações de permissão
- Nunca exibidas na UI

---

## Fluxo de Verificação (Backend)

```python
# require_permission("order:read")
def dependency(user: User = Depends(get_current_user)):
    if PermissionService.has_role(user, "tech"):
        return True  # tech bypassa tudo
    permissions = PermissionService.get_user_permissions(user)
    if "order:read" not in permissions:
        raise HTTPException(403)
```

```python
# require_any_permission("client:read", "order:create")
# Permite acesso se o usuário tem QUALQUER UMA das permissões listadas.
# Usado em GET /clients/ e GET /products/ para que vendedores possam
# carregar clientes/produtos no formulário de criação de pedidos.
```

---

## Fluxo de Verificação (Frontend)

O componente `RequirePermissionOrRedirect` protege as rotas:

```tsx
<RequirePermissionOrRedirect permission="order:read" fallbackTo="/admin">
  <Orders />
</RequirePermissionOrRedirect>
```

Se o usuário não tem a permissão, é redirecionado para `fallbackTo`.

O `PrivateRoute` mostra um loading spinner enquanto as permissões são carregadas de `/auth/me`,
garantindo que `RequirePermissionOrRedirect` nunca avalie com permissões vazias.

---

## Mapa de Rotas → Permissões

| Rota frontend           | Permissão necessária  | Endpoint API               |
|-------------------------|-----------------------|----------------------------|
| `/admin/dashboard`      | `dashboard:read`      | `GET /dashboard/...`       |
| `/admin/orders`         | `order:read`          | `GET /orders/`             |
| `/admin/orders/:id`     | `order:read`          | `GET /orders/:id`          |
| `/admin/seller`         | `order:list`          | `GET /orders/seller`       |
| `/admin/seller/orders/:id` | `order:list`       | `GET /orders/seller/:id`   |
| `/admin/producer`       | `order:produce`       | `POST /orders/producer/next` |
| `/admin/fiscal`         | `order:bill`          | `GET /orders/fiscal`       |
| `/admin/fiscal/orders/:id` | `order:bill`       | `GET /orders/fiscal/:id`   |
| `/admin/products`       | `product:read`        | `GET /products/`           |
| `/admin/clients`        | `client:read`         | `GET /clients/`            |
| `/admin/users`          | `user:create`         | `GET /users/`              |
| `/admin/audit`          | `audit:read`          | `GET /audit/`              |

---

## Adicionando Nova Permissão

1. **Criar permissão no BD** (migration Alembic):
   ```sql
   INSERT INTO permissions (code, name, description) VALUES ('novo:codigo', 'Nome', 'Descrição');
   ```

2. **Atribuir ao grupo de menu** relevante:
   ```sql
   INSERT INTO menu_group_permissions (menu_group_id, permission_id)
   SELECT mg.id, p.id FROM menu_groups mg, permissions p
   WHERE mg.code = 'orders' AND p.code = 'novo:codigo';
   ```

3. **Proteger o endpoint** (API):
   ```python
   dependencies=[Depends(require_permission("novo:codigo"))]
   ```

4. **Proteger a rota** (Frontend):
   ```tsx
   <RequirePermissionOrRedirect permission="novo:codigo" fallbackTo="/admin">
     <NovaPage />
   </RequirePermissionOrRedirect>
   ```

5. **Adicionar ao menu lateral** (`DesktopNavbar/index.tsx`):
   ```tsx
   { text: 'Nova Página', icon: <NovoIcon />, path: '/admin/nova', permission: 'novo:codigo' }
   ```
