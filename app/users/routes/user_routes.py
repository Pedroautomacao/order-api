from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import or_, func, text
from sqlalchemy.orm import Session, selectinload

from app.core.security import hash_password
from app.core.utils.search import normalize_search_string, unaccent_like_sql
from app.database.deps import get_db
from app.users.models.user import User
from app.users.models.role import Role
from app.users.models.menu_group import MenuGroup
from app.users.models.permission import Permission
from app.users.schemas.user_schema import (
    UserCreate,
    UserUpdate,
    UserResponse,
    ResetPasswordRequest,
    ChangePasswordRequest,
)
from app.users.schemas.role_schema import (
    RoleResponse,
    MenuGroupResponse,
    RoleUpdate,
    MenuGroupCreate,
    MenuGroupUpdate,
    PermissionResponse,
)
from app.users.services.user_service import UserService
from app.users.services.permission_service import PermissionService
from app.users.dependencies.permission_dependencies import require_permission
from app.users.dependencies.auth_dependencies import get_current_user
from app.audit.services.audit_service import AuditService

router = APIRouter()


def require_can_get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
):
    """Allow user to get their own profile (for loading permissions); otherwise require user:create."""
    if user_id == current_user.id:
        return
    if "user:create" not in PermissionService.get_user_permissions(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


@router.post(
    "/",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("user:create"))],
)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return UserService.create(
        db=db,
        data=data,
        current_user=current_user,
    )


@router.get(
    "/",
    response_model=list[UserResponse],
    dependencies=[Depends(require_permission("user:create"))],
)
def list_users(
    db: Session = Depends(get_db),
    search: str | None = Query(None, description="ID ou nome do usuário"),
    is_active: bool | None = Query(None, description="Filtrar por ativo (true/false); omitir = todos"),
):
    q = (
        db.query(User)
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.roles).selectinload(Role.menu_groups).selectinload(MenuGroup.permissions),
        )
        .filter(User.is_deleted.is_(False))
    )
    if is_active is not None:
        q = q.filter(User.is_active.is_(is_active))
    if search and search.strip():
        normalized = normalize_search_string(search)
        pattern = f"%{normalized}%"
        conditions = []
        if search.strip().isdigit():
            conditions.append(User.id == int(search.strip()))
        use_unaccent = db.get_bind().dialect.name == "postgresql"
        if use_unaccent:
            conditions.append(
                text(
                    unaccent_like_sql(
                        [
                            ("users", "username"),
                            ("users", "first_name"),
                            ("users", "last_name"),
                        ]
                    )
                ).bindparams(search_pattern=pattern)
            )
        else:
            conditions.append(func.lower(User.username).like(pattern))
            conditions.append(func.lower(User.first_name).like(pattern))
            conditions.append(func.lower(User.last_name).like(pattern))
        q = q.filter(or_(*conditions))
    return q.order_by(User.username).all()


# Perfis ocultos: não aparecem na UI de gestão de usuários (atribuídos só manualmente)
HIDDEN_ROLE_NAMES = ("Tech",)


@router.get(
    "/roles/list",
    response_model=list[RoleResponse],
    dependencies=[Depends(require_permission("user:create"))],
)
def list_roles(db: Session = Depends(get_db)):
    return (
        db.query(Role)
        .filter(Role.name.notin_(HIDDEN_ROLE_NAMES))
        .options(
            selectinload(Role.permissions),
            selectinload(Role.menu_groups),
        )
        .order_by(Role.name)
        .all()
    )


# Permissões ocultas: não aparecem na UI ao editar grupos de menu / perfis (ex: tech)
HIDDEN_PERMISSION_PREFIXES = ("tech",)

def _is_hidden_permission(code: str) -> bool:
    if not code:
        return False
    return code in HIDDEN_PERMISSION_PREFIXES or code.split(":")[0] in HIDDEN_PERMISSION_PREFIXES


@router.get(
    "/permissions",
    response_model=list[PermissionResponse],
    dependencies=[Depends(require_permission("user:create"))],
)
def list_permissions(db: Session = Depends(get_db)):
    all_perms = db.query(Permission).order_by(Permission.code).all()
    return [p for p in all_perms if not _is_hidden_permission(p.code)]


@router.get(
    "/menu-groups",
    response_model=list[MenuGroupResponse],
    dependencies=[Depends(require_permission("user:create"))],
)
def list_menu_groups(db: Session = Depends(get_db)):
    return (
        db.query(MenuGroup)
        .options(selectinload(MenuGroup.permissions))
        .order_by(MenuGroup.name)
        .all()
    )


@router.post(
    "/menu-groups",
    response_model=MenuGroupResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("user:create"))],
)
def create_menu_group(
    data: MenuGroupCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(MenuGroup).filter(MenuGroup.code == data.code.strip()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Já existe um grupo com este código",
        )
    permissions = db.query(Permission).filter(Permission.id.in_(data.permission_ids)).all()
    if len(permissions) != len(data.permission_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uma ou mais permissões inválidas",
        )
    group = MenuGroup(
        code=data.code.strip(),
        name=data.name.strip(),
        description=data.description.strip() if data.description else None,
    )
    group.permissions = permissions
    db.add(group)
    db.commit()
    db.refresh(group)
    AuditService.log(
        db=db,
        action="menu_group:create",
        entity="menu_group",
        entity_id=group.id,
        user_id=current_user.id,
        description=f"Grupo de menu '{group.name}' (code={group.code}) criado por {current_user.username}",
    )
    return group


@router.put(
    "/menu-groups/{group_id}",
    response_model=MenuGroupResponse,
    dependencies=[Depends(require_permission("user:create"))],
)
def update_menu_group(
    group_id: int,
    data: MenuGroupUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    group = (
        db.query(MenuGroup)
        .options(selectinload(MenuGroup.permissions))
        .filter(MenuGroup.id == group_id)
        .first()
    )
    if not group:
        raise HTTPException(status_code=404, detail="Grupo não encontrado")
    if data.name is not None:
        group.name = data.name.strip()
    if data.description is not None:
        group.description = data.description.strip() if data.description else None
    if data.permission_ids is not None:
        permissions = (
            db.query(Permission).filter(Permission.id.in_(data.permission_ids)).all()
        )
        if len(permissions) != len(data.permission_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uma ou mais permissões inválidas",
            )
        group.permissions = permissions
    db.commit()
    db.refresh(group)
    AuditService.log(
        db=db,
        action="menu_group:update",
        entity="menu_group",
        entity_id=group.id,
        user_id=current_user.id,
        description=f"Grupo de menu '{group.name}' (id={group_id}) atualizado por {current_user.username}",
    )
    return group


@router.put(
    "/roles/{role_id}",
    response_model=RoleResponse,
    dependencies=[Depends(require_permission("user:create"))],
)
def update_role(
    role_id: int,
    data: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    role = db.query(Role).options(
        selectinload(Role.permissions),
        selectinload(Role.menu_groups),
    ).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if data.name is not None:
        role.name = data.name
    if data.menu_group_ids is not None:
        groups = db.query(MenuGroup).filter(MenuGroup.id.in_(data.menu_group_ids)).all()
        role.menu_groups = groups
    db.commit()
    db.refresh(role)
    AuditService.log(
        db=db,
        action="role:update",
        entity="role",
        entity_id=role.id,
        user_id=current_user.id,
        description=f"Perfil '{role.name}' (id={role_id}) atualizado por {current_user.username}",
    )
    role = (
        db.query(Role)
        .options(
            selectinload(Role.permissions),
            selectinload(Role.menu_groups),
        )
        .filter(Role.id == role_id)
        .first()
    )
    return role


@router.get(
    "/me",
    response_model=UserResponse,
)
def get_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return current authenticated user with roles and permissions (e.g. after F5)."""
    user = (
        db.query(User)
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.roles).selectinload(Role.menu_groups).selectinload(MenuGroup.permissions),
        )
        .filter(
            User.id == current_user.id,
            User.is_deleted.is_(False),
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_can_get_user)],
)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.roles).selectinload(Role.menu_groups).selectinload(MenuGroup.permissions),
        )
        .filter(
            User.id == user_id,
            User.is_deleted.is_(False),
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permission("user:update"))],
)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = (
        db.query(User)
        .options(
            selectinload(User.roles).selectinload(Role.permissions),
            selectinload(User.roles).selectinload(Role.menu_groups).selectinload(MenuGroup.permissions),
        )
        .filter(
            User.id == user_id,
            User.is_deleted.is_(False),
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserService.update(
        db=db,
        user=user,
        data=data,
        current_user=current_user,
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("user:delete"))],
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own user",
        )

    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.is_deleted.is_(False),
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    UserService.delete(
        db=db,
        user=user,
        current_user=current_user,
    )


@router.put(
    "/{user_id}/reset-password",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("user:reset_password"))],
)
def reset_user_password(
    user_id: int,
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    user = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.is_deleted.is_(False),
        )
        .first()
    )

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    UserService.reset_password(
        db=db,
        user=user,
        new_password=data.new_password,
        admin_user=current_user,
    )


@router.put(
    "/me/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
)
def change_own_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Usuário logado troca a própria senha (exige senha atual)."""
    UserService.change_own_password(
        db=db,
        user=current_user,
        current_password=data.current_password,
        new_password=data.new_password,
    )
