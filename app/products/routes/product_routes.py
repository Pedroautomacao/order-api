from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import or_, func, text
from sqlalchemy.orm import Session

from app.database.deps import get_db
from app.products.exception_handler import UnitOfMeasureNotFoundException, ProductNotFoundException
from app.products.models.product import Product
from app.core.utils.search import normalize_search_string, unaccent_like_sql
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
    dependencies=[Depends(require_permission("product:read"))],
)
def list_products(
    db: Session = Depends(get_db),
    search: str | None = Query(None, description="ID do produto, SKU ou nome"),
    is_active: bool | None = Query(None, description="Filtrar por ativo (true/false); omitir = todos"),
):
    q = db.query(Product).filter(Product.is_deleted.is_(False))
    if is_active is not None:
        q = q.filter(Product.is_active.is_(is_active))
    if search and search.strip():
        normalized = normalize_search_string(search)
        pattern = f"%{normalized}%"
        conditions = []
        if search.strip().isdigit():
            conditions.append(Product.id == int(search.strip()))
        use_unaccent = db.get_bind().dialect.name == "postgresql"
        if use_unaccent:
            conditions.append(
                text(unaccent_like_sql([("products", "sku"), ("products", "name")])).bindparams(
                    search_pattern=pattern
                )
            )
        else:
            conditions.append(func.lower(Product.sku).like(pattern))
            conditions.append(func.lower(Product.name).like(pattern))
        q = q.filter(or_(*conditions))
    return q.order_by(Product.name).all()


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(require_permission("product:read"))],
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
