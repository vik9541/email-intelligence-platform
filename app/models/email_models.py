"""
Email Models for Classification System
Pydantic models for EmailDocument, Classification, etc.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class EmailCategory(str, Enum):
    """Email classification categories"""
    INVOICE = "invoice"
    PURCHASE_ORDER = "purchase_order"
    SUPPORT = "support"
    SALES = "sales"
    HR = "hr"
    OTHER = "other"


class EmailDocument(BaseModel):
    """Email document для классификации"""
    message_id: str = Field(..., description="Unique message ID")
    from_email: str = Field(..., description="Sender email address")
    to_email: str = Field(..., description="Recipient email address")
    subject: str = Field(default="", description="Email subject")
    body_text: str = Field(default="", description="Email body (plain text)")
    size_bytes: int = Field(default=0, description="Email size in bytes")
    received_at: datetime = Field(..., description="When email was received")


class Classification(BaseModel):
    """Classification result"""
    category: EmailCategory = Field(..., description="Classified category")
    confidence: float = Field(..., description="Confidence score (0.0-1.0)", ge=0.0, le=1.0)
    priority: int = Field(default=5, description="Priority (1=highest, 10=lowest)", ge=1, le=10)
    reasoning: str = Field(default="", description="Why this classification")
    requires_review: bool = Field(default=False, description="Needs human review")
