"""
ORM модель Email.
"""

from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, String, Text
from sqlalchemy.orm import relationship

from app.models.base import Base


class Email(Base):
    """ORM модель для таблицы emails."""

    __tablename__ = "emails"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    subject = Column(String(500), nullable=True)
    sender = Column(String(255), nullable=False)
    recipient = Column(String(255), nullable=False)
    body = Column(Text, nullable=True)
    received_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationship к действиям
    actions = relationship("EmailAction", back_populates="email", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Email(id={self.id}, subject={self.subject[:50] if self.subject else None})>"
