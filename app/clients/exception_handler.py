from app.core.exceptions import DomainException


class ClientNotFoundException(DomainException):
    def __init__(self, client_id: int | None = None):
        message = (
            f"Client not found (id={client_id})"
            if client_id
            else "Client not found"
        )
        super().__init__(message)
