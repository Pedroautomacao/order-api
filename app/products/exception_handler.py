from app.core.exceptions import DomainException


class ProductNotFoundException(DomainException):
    status_code = 404

    def __init__(self, product_id: int):
        super().__init__(f"Product not found (id={product_id})")


class UnitOfMeasureNotFoundException(DomainException):
    status_code = 404

    def __init__(self, unit_id: int):
        super().__init__(
            f"Unit of measure not found (id={unit_id})"
        )
