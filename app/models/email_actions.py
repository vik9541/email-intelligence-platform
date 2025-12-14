"""
ORM модель для таблицы emailactions - хранение действий по email.
"""
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from app.models.base import Base


class EmailAction(Base):
    """
    ORM модель для таблицы emailactions.
    Хранит информацию о действиях, выполненных по результатам анализа email.
    """
    __tablename__ = "emailactions"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    emailid = Column(
        BigInteger,
        ForeignKey("emails.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actiontype = Column(
        String(50),
        nullable=False,
        comment="Тип действия: createorder, updateinvoice, createticket, sendquote",
    )
    actionpayload = Column(
        JSONB,
        nullable=True,
        comment="JSON с параметрами действия",
    )
    erpentitytype = Column(
        String(50),
        nullable=True,
        comment="Тип сущности ERP: Order, Invoice, Ticket, Quote",
    )
    erpentityid = Column(
        PG_UUID(as_uuid=True),
        nullable=True,
        comment="UUID созданной/обновленной сущности в ERP",
    )
    status = Column(
        String(50),
        nullable=False,
        default="pending",
        comment="Статус: pending, executing, completed, failed",
    )
    errormessage = Column(
        Text,
        nullable=True,
        comment="Сообщение об ошибке при неудачном выполнении",
    )
    retrycount = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Количество попыток выполнения",
    )
    executedat = Column(
        DateTime,
        nullable=True,
        comment="Время выполнения действия",
    )
    createdat = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Время создания записи",
    )

    # Relationship к email
    email = relationship("Email", back_populates="actions")

    def __repr__(self) -> str:
        return (
            f"<EmailAction(id={self.id}, emailid={self.emailid}, "
            f"actiontype={self.actiontype}, status={self.status})>"
        )

    def mark_executing(self) -> None:
        """Отметить действие как выполняющееся."""
        self.status = "executing"
        self.executedat = datetime.now(UTC)

    def mark_completed(
        self,
        erp_entity_type: str,
        erp_entity_id: UUID,
    ) -> None:
        """Отметить действие как успешно выполненное."""
        self.status = "completed"
        self.erpentitytype = erp_entity_type
        self.erpentityid = erp_entity_id
        self.executedat = datetime.now(UTC)

    def mark_failed(self, error_message: str) -> None:
        """Отметить действие как неудачное."""
        self.status = "failed"
        self.errormessage = error_message
        if self.retrycount is None:
            self.retrycount = 0
        self.retrycount += 1
        self.executedat = datetime.now(UTC)
