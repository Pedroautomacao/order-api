from app.users.models.user import User


class PermissionService:
    @staticmethod
    def get_user_permissions(user: User) -> set[str]:
        permissions: set[str] = set()

        for role in user.roles:
            for permission in role.permissions:
                permissions.add(permission.code)

        return permissions

    @staticmethod
    def has_role(user: User, role_name: str) -> bool:
        return any(role.name == role_name for role in user.roles)
