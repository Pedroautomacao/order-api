from sqlalchemy import String, CHAR, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.database.mixins import AuditMixin


class Client(Base, AuditMixin):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cpf_cnpj: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    priority: Mapped[str] = mapped_column(CHAR(1), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    phone_number: Mapped[str] = mapped_column(String(30), nullable=False)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
