"""Rótulos em português para a tela de auditoria.

`action` e `entity` são gravados como chave estável ("order:create") e nunca
traduzidos no banco: o histórico já registrado continuaria com o valor antigo e
os filtros deixariam de casar. A tradução acontece só na exibição.
"""

ACTION_LABELS: dict[str, str] = {
    # Pedidos
    "order:create": "Pedido criado",
    "order:update": "Pedido editado",
    "order:assign": "Pedido atribuído à produção",
    "order:finish": "Produção finalizada",
    "order:reset_production": "Produção reiniciada",
    "order:cancel": "Pedido cancelado",
    "order:bill": "Pedido faturado",
    "order:mark_paid": "Pedido marcado como pago",
    "order:set_priority": "Prioridade alterada",
    "order:reschedule": "Data de entrega remarcada",
    # Itens do pedido
    "order:item_confirm": "Item confirmado",
    "order:item_update_quantity": "Quantidade produzida corrigida",
    # Clientes
    "client:create": "Cliente cadastrado",
    "client:update": "Cliente atualizado",
    "client:delete": "Cliente excluído",
    # Produtos
    "product:create": "Produto cadastrado",
    "product:update": "Produto atualizado",
    "product:delete": "Produto excluído",
    # Unidades de medida
    "unit:create": "Unidade cadastrada",
    "unit:update": "Unidade atualizada",
    "unit:delete": "Unidade excluída",
    # Usuários e acesso
    "user:create": "Usuário cadastrado",
    "user:update": "Usuário atualizado",
    "user:delete": "Usuário excluído",
    "user:reset_password": "Senha redefinida pelo administrador",
    "user:change_password": "Senha alterada pelo próprio usuário",
    "role:update": "Perfil de acesso atualizado",
    "menu_group:create": "Grupo de menu criado",
    "menu_group:update": "Grupo de menu atualizado",
}

ENTITY_LABELS: dict[str, str] = {
    "order": "Pedido",
    "order_item": "Item do pedido",
    "client": "Cliente",
    "product": "Produto",
    "unit_of_measure": "Unidade de medida",
    "user": "Usuário",
    "role": "Perfil de acesso",
    "menu_group": "Grupo de menu",
}


def action_label(action: str | None) -> str:
    """Rótulo da ação; devolve a própria chave se ainda não houver tradução."""
    if not action:
        return "-"
    return ACTION_LABELS.get(action, action)


def entity_label(entity: str | None) -> str:
    if not entity:
        return "-"
    return ENTITY_LABELS.get(entity, entity)
