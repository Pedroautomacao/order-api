from sqlalchemy.orm import Session

from app.core.services.base_atomic_service import BaseAtomicService
from app.products.exception_handler import UnitOfMeasureNotFoundException
from app.products.models.product import Product
from app.products.schemas.product_schema import ProductCreate, ProductUpdate
from app.audit.services.audit_service import AuditService
from app.units.models.unit_of_measure import UnitOfMeasure
from app.users.models import User


class ProductService(BaseAtomicService):
    @staticmethod
    def create(
        db: Session,
        *,
        data: ProductCreate,
        current_user: User,
    ) -> Product:

        unit = (
            db.query(UnitOfMeasure)
            .filter(
                UnitOfMeasure.id == data.unit_of_measure_id,
                UnitOfMeasure.is_deleted.is_(False),
                UnitOfMeasure.is_active.is_(True),
            )
            .first()
        )

        if not unit:
            raise UnitOfMeasureNotFoundException(data.unit_of_measure_id)

        product = Product(
            name=data.name,
            description=data.description,
            sku=data.sku,
            is_active=data.is_active,
            unit_of_measure_id=unit.id,
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
        payload = data.model_dump(exclude_unset=True)

        # tratar unit_of_measure_id separadamente
        if "unit_of_measure_id" in payload:
            unit_id = payload.pop("unit_of_measure_id")

            unit = (
                db.query(UnitOfMeasure)
                .filter(
                    UnitOfMeasure.id == unit_id,
                    UnitOfMeasure.is_deleted.is_(False),
                    UnitOfMeasure.is_active.is_(True),
                )
                .first()
            )

            if not unit:
                raise UnitOfMeasureNotFoundException(unit_id)

            product.unit_of_measure_id = unit.id

        for field, value in payload.items():
            setattr(product, field, value)

        db.commit()
        db.refresh(product)

        AuditService.log(
            db=db,
            action="product:update",
            entity="product",
            entity_id=product.id,
            user_id=current_user.id,
            description=(
                f"Product {product.name} updated by "
                f"{current_user.username}"
            ),
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
