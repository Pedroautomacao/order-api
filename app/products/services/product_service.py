from uuid import uuid4

from sqlalchemy.orm import Session

from app.database.atomic import atomic
from app.products.exception_handler import UnitOfMeasureNotFoundException
from app.products.models.product import Product
from app.products.schemas.product_schema import ProductCreate, ProductUpdate
from app.audit.services.audit_service import AuditService
from app.units.models.unit_of_measure import UnitOfMeasure
from app.users.models import User


class ProductService:
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
            # O sku é o id do produto, que só existe depois do INSERT — e a
            # coluna é NOT NULL. Entra um placeholder único e ele é sobrescrito
            # abaixo, na mesma transação, então o temporário nunca fica visível.
            sku=f"tmp-{uuid4().hex}",
            is_active=data.is_active,
            unit_price=data.unit_price,
            unit_of_measure_id=unit.id,
        )
        with atomic(db):
            db.add(product)
            db.flush()  # precisa do id gerado para o log e para o sku

            product.sku = str(product.id)
            db.flush()

            AuditService.log(
                db=db,
                action="product:create",
                entity="product",
                entity_id=product.id,
                user_id=current_user.id,
                description=f"Produto {product.name} cadastrado",
            )

        db.refresh(product)
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

        with atomic(db):
            for field, value in payload.items():
                setattr(product, field, value)

            AuditService.log(
                db=db,
                action="product:update",
                entity="product",
                entity_id=product.id,
                user_id=current_user.id,
                description=f"Produto {product.name} atualizado",
            )

        db.refresh(product)
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

        with atomic(db):
            product.is_deleted = True

            AuditService.log(
                db=db,
                action="product:delete",
                entity="product",
                entity_id=product.id,
                user_id=current_user.id,
                description=f"Produto {product.name} excluído",
            )
