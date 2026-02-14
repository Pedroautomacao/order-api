from fastapi import Depends, HTTPException, status

from app.users.dependencies.auth_dependencies import get_current_user
from app.users.services.permission_service import PermissionService
from app.users.models.user import User


def require_permission(permission_code: str):
    def dependency(user: User = Depends(get_current_user)):
        # 🔧 TECH ROLE → BYPASS TOTAL
        if PermissionService.has_role(user, "tech"):
            return True

        # Permissões vêm de role.permissions e de role.menu_groups (grupos de menu)
        permissions = PermissionService.get_user_permissions(user)
        if permission_code in permissions:
            return True

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )

    return dependency
