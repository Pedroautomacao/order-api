from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.products.exception_handler import UnitOfMeasureNotFoundException, ProductNotFoundException
from app.products.models.product import Product
from app.products.schemas.product_schema import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
)
from app.products.services.product_service import ProductService
from app.users.dependencies.permission_dependencies import require_permission
from app.users.dependencies.auth_dependencies import get_current_user

router = APIRouter()


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("product:create"))],
)
def create_product(
    data: ProductCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return ProductService.create(
            db=db,
            data=data,
            current_user=current_user,
        )
    except UnitOfMeasureNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.get(
    "/",
    response_model=list[ProductResponse],
    dependencies=[Depends(require_permission("product:create"))],
)
def list_products(db: Session = Depends(get_db)):
    return (
        db.query(Product)
        .filter(Product.is_deleted.is_(False))
        .order_by(Product.name)
        .all()
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(require_permission("product:create"))],
)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.is_deleted.is_(False),
        )
        .first()
    )

    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(require_permission("product:update"))],
)
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.is_deleted.is_(False),
        )
        .first()
    )

    if not product:
        raise ProductNotFoundException(product_id)

    try:
        return ProductService.update(
            db=db,
            product=product,
            data=data,
            current_user=current_user,
        )
    except UnitOfMeasureNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("product:delete"))],
)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    product = (
        db.query(Product)
        .filter(
            Product.id == product_id,
            Product.is_deleted.is_(False),
        )
        .first()
    )

    if not product:
        raise ProductNotFoundException(product_id)

    ProductService.delete(
        db=db,
        product=product,
        current_user=current_user,
    )
