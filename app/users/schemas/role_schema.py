from pydantic import BaseModel


class PermissionResponse(BaseModel):
    id: int
    code: str
    description: str | None

    class Config:
        from_attributes = True


class MenuGroupResponse(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    permissions: list["PermissionResponse"] = []

    class Config:
        from_attributes = True


class RoleResponse(BaseModel):
    id: int
    name: str
    permissions: list[PermissionResponse] = []
    menu_groups: list[MenuGroupResponse] = []

    class Config:
        from_attributes = True


class RoleUpdate(BaseModel):
    name: str | None = None
    menu_group_ids: list[int] | None = None


class MenuGroupCreate(BaseModel):
    code: str
    name: str
    description: str | None = None
    permission_ids: list[int]


class MenuGroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    permission_ids: list[int] | None = None
