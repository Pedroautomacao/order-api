from app.users.models.user import User


class PermissionService:
    @staticmethod
    def get_user_permissions(user: User) -> set[str]:
        permissions: set[str] = set()

        for role in user.roles:
            menu_groups = getattr(role, "menu_groups", None) or []
            if menu_groups:
                # Se o perfil tem grupos de menu, usa só as permissões dos grupos (não as diretas do role)
                for menu_group in menu_groups:
                    for permission in menu_group.permissions:
                        permissions.add(permission.code)
            else:
                # Perfil sem grupos de menu: usa as permissões diretas do role
                for permission in role.permissions:
                    permissions.add(permission.code)

        return permissions

    @staticmethod
    def has_role(user: User, role_name: str) -> bool:
        return any(role.name == role_name for role in user.roles)
