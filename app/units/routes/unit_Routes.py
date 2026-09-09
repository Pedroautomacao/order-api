from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.units.models.unit_of_measure import UnitOfMeasure
from app.units.schemas.unit_schema import (
    UnitCreate,
    UnitUpdate,
    UnitResponse,
)
from app.units.services.unit_service import UnitService
from app.units.exception_handler import UnitNotFoundException
from app.users.dependencies.permission_dependencies import require_permission
from app.users.dependencies.auth_dependencies import get_current_user

router = APIRouter()


@router.post(
    "",
    response_model=UnitResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("product:create"))],
)
def create_unit(
    data: UnitCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return UnitService.create(
        db=db,
        data=data,
        current_user=current_user,
    )


@router.get(
    "",
    response_model=list[UnitResponse],
    dependencies=[Depends(require_permission("product:read"))],
)
def list_units(db: Session = Depends(get_db)):
    return (
        db.query(UnitOfMeasure)
        .filter(
            UnitOfMeasure.is_deleted.is_(False),
            UnitOfMeasure.is_active.is_(True),
        )
        .order_by(UnitOfMeasure.name)
        .all()
    )


@router.put(
    "/{unit_id}",
    response_model=UnitResponse,
    dependencies=[Depends(require_permission("product:update"))],
)
def update_unit(
    unit_id: int,
    data: UnitUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    unit = (
        db.query(UnitOfMeasure)
        .filter(
            UnitOfMeasure.id == unit_id,
            UnitOfMeasure.is_deleted.is_(False),
        )
        .first()
    )

    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    return UnitService.update(
        db=db,
        unit=unit,
        data=data,
        current_user=current_user,
    )


@router.delete(
    "/{unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("product:delete"))],
)
def delete_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    unit = (
        db.query(UnitOfMeasure)
        .filter(
            UnitOfMeasure.id == unit_id,
            UnitOfMeasure.is_deleted.is_(False),
        )
        .first()
    )

    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")

    UnitService.delete(
        db=db,
        unit=unit,
        current_user=current_user,
    )
