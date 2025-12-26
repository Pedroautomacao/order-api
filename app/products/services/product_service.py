from sqlalchemy.orm import Session

from app.products.models.product import Product
from app.products.schemas.product_schema import ProductCreate, ProductUpdate
from app.audit.services.audit_service import AuditService
from app.users.models import User


class ProductService:
    @staticmethod
    def create(
        db: Session,
        *,
        data: ProductCreate,
        current_user: User,
    ) -> Product:
        product = Product(
            name=data.name,
            description=data.description,
            sku=data.sku,
            is_active=data.is_active,
        )
        db.add(product)
        db.commit()
        db.refresh(product)

        AuditService.log(
            db=db,
            action="product:create",
            entity="product",
            entity_id=product.id,
            user_id=current_user.id,
            description=f"Product {product.name} created by {current_user.username}",
        )

        return product

    @staticmethod
    def update(
        db: Session,
        *,
        product: Product,
        data: ProductUpdate,
        current_user: User,
    ) -> Product:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(product, field, value)

        db.commit()
        db.refresh(product)

        AuditService.log(
            db=db,
            action="product:update",
            entity="product",
            entity_id=product.id,
            user_id=current_user.id,
            description=f"Product {product.name} updated by {current_user.username}",
        )

        return product

    @staticmethod
    def delete(
        db: Session,
        *,
        product: Product,
        current_user: User,
    ) -> None:
        if product.is_deleted:
            return

        product.is_deleted = True
        db.commit()

        AuditService.log(
            db=db,
            action="product:delete",
            entity="product",
            entity_id=product.id,
            user_id=current_user.id,
            description=f"Product {product.name} soft deleted by {current_user.username}",
        )
