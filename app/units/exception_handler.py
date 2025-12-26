from app.core.exceptions import DomainException


class UnitNotFoundException(DomainException):
    def __init__(self, unit_id: int):
        super().__init__(
            f"Unit of measure not found (id={unit_id})"
        )