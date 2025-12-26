from fastapi import APIRouter, Depends

from app.users.dependencies.permission_dependencies import require_permission

router = APIRouter()


@router.get(
    "/admin-only",
    dependencies=[Depends(require_permission("user:create"))],
)
def admin_only():
    return {"message": "Admin access granted"}
