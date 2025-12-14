"""
Pydantic СЃС…РµРјС‹ РґР»СЏ ERP РёРЅС‚РµРіСЂР°С†РёРё.
"""
from decimal import Decimal
from enum import Enum
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ActionStatus(str, Enum):
    """РЎС‚Р°С‚СѓСЃ РІС‹РїРѕР»РЅРµРЅРёСЏ РґРµР№СЃС‚РІРёСЏ."""
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"


class OrderStatus(str, Enum):
    """РЎС‚Р°С‚СѓСЃ Р·Р°РєР°Р·Р° РІ ERP."""
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class OrderItem(BaseModel):
    """РџРѕР·РёС†РёСЏ Р·Р°РєР°Р·Р°."""
    productcode: str = Field(..., description="РљРѕРґ С‚РѕРІР°СЂР°/Р°СЂС‚РёРєСѓР»")
    description: str = Field(default="", description="РћРїРёСЃР°РЅРёРµ С‚РѕРІР°СЂР°")
    quantity: Decimal = Field(..., gt=0, description="РљРѕР»РёС‡РµСЃС‚РІРѕ")
    unitprice: Decimal | None = Field(default=None, ge=0, description="Р¦РµРЅР° Р·Р° РµРґРёРЅРёС†Сѓ")
    unit: str = Field(default="С€С‚", description="Р•РґРёРЅРёС†Р° РёР·РјРµСЂРµРЅРёСЏ")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "productcode": "SKU-12345",
                "description": "РќРѕСѓС‚Р±СѓРє ASUS VivoBook",
                "quantity": "2",
                "unitprice": "45000.00",
                "unit": "С€С‚",
            }
        }
    )


class ERPOrder(BaseModel):
    """Р—Р°РєР°Р· РІ ERP СЃРёСЃС‚РµРјРµ."""
    id: UUID = Field(..., description="UUID Р·Р°РєР°Р·Р° РІ ERP")
    number: str = Field(..., description="РќРѕРјРµСЂ Р·Р°РєР°Р·Р°")
    status: OrderStatus = Field(default=OrderStatus.DRAFT, description="РЎС‚Р°С‚СѓСЃ Р·Р°РєР°Р·Р°")
    customer_id: UUID = Field(..., description="UUID РєР»РёРµРЅС‚Р°")
    items: list[OrderItem] = Field(default_factory=list, description="РџРѕР·РёС†РёРё Р·Р°РєР°Р·Р°")
    total_amount: Decimal | None = Field(default=None, description="РћР±С‰Р°СЏ СЃСѓРјРјР°")
    source: str = Field(default="email", description="РСЃС‚РѕС‡РЅРёРє Р·Р°РєР°Р·Р°")
    source_email_id: int | None = Field(default=None, description="ID РёСЃС…РѕРґРЅРѕРіРѕ email")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "number": "ORD-2024-001234",
                "status": "draft",
                "customer_id": "123e4567-e89b-12d3-a456-426614174001",
                "items": [],
                "total_amount": "90000.00",
                "source": "email",
                "source_email_id": 42,
            }
        }
    )


class ActionResult(BaseModel):
    """Р РµР·СѓР»СЊС‚Р°С‚ РІС‹РїРѕР»РЅРµРЅРёСЏ РґРµР№СЃС‚РІРёСЏ."""
    status: ActionStatus = Field(..., description="РЎС‚Р°С‚СѓСЃ РІС‹РїРѕР»РЅРµРЅРёСЏ")
    erp_entity_id: UUID | None = Field(default=None, description="UUID СЃРѕР·РґР°РЅРЅРѕР№ СЃСѓС‰РЅРѕСЃС‚Рё")
    message: str | None = Field(default=None, description="РЎРѕРѕР±С‰РµРЅРёРµ РѕР± СѓСЃРїРµС…Рµ")
    error: str | None = Field(default=None, description="РЎРѕРѕР±С‰РµРЅРёРµ РѕР± РѕС€РёР±РєРµ")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "success",
                "erp_entity_id": "123e4567-e89b-12d3-a456-426614174000",
                "message": "Order ORD-2024-001234 created",
                "error": None,
            }
        }
    )



class InvoiceStatus(str, Enum):
    """Статус счёта в ERP."""
    DRAFT = "draft"
    SENT = "sent"
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class TicketPriority(int, Enum):
    """риоритет тикета."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class TicketStatus(str, Enum):
    """Статус тикета в системе поддержки."""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ERPInvoice(BaseModel):
    """Счёт в ERP системе."""
    id: UUID = Field(..., description="UUID счёта в ERP")
    number: str = Field(..., description="омер счёта")
    status: InvoiceStatus = Field(..., description="Статус счёта")
    amount: Decimal = Field(..., description="Сумма счёта")
    customer_id: UUID = Field(..., description="UUID клиента")
    notes: str | None = Field(default=None, description="римечания")
    updated_at: datetime | None = Field(default=None, description="ремя обновления")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "number": "INV-2024-001234",
                "status": "paid",
                "amount": "50000.00",
                "customer_id": "123e4567-e89b-12d3-a456-426614174001",
                "notes": "Payment confirmed via email",
            }
        }
    )


class ERPTicket(BaseModel):
    """Тикет в системе поддержки."""
    id: UUID = Field(..., description="UUID тикета")
    number: str = Field(..., description="омер тикета")
    subject: str = Field(..., description="Тема тикета")
    description: str = Field(default="", description="писание проблемы")
    status: TicketStatus = Field(default=TicketStatus.OPEN, description="Статус тикета")
    customer_id: UUID = Field(..., description="UUID клиента")
    priority: TicketPriority = Field(default=TicketPriority.MEDIUM, description="риоритет")
    source_email_id: int | None = Field(default=None, description="ID исходного email")
    created_at: datetime | None = Field(default=None, description="ремя создания")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "number": "TKT-2024-001234",
                "subject": "роблема с доставкой",
                "description": "аказ не доставлен в срок",
                "status": "open",
                "customer_id": "123e4567-e89b-12d3-a456-426614174001",
                "priority": 2,
            }
        }
    )

class EmailActionResult(BaseModel):
    """Р РµР·СѓР»СЊС‚Р°С‚ РґРµР№СЃС‚РІРёСЏ РїРѕ email РґР»СЏ API РѕС‚РІРµС‚Р°."""
    action_id: int = Field(..., description="ID РґРµР№СЃС‚РІРёСЏ РІ Р‘Р”")
    email_id: int = Field(..., description="ID email")
    action_type: str = Field(..., description="РўРёРї РґРµР№СЃС‚РІРёСЏ")
    status: ActionStatus = Field(..., description="РЎС‚Р°С‚СѓСЃ")
    erp_entity_type: str | None = Field(default=None, description="РўРёРї СЃСѓС‰РЅРѕСЃС‚Рё ERP")
    erp_entity_id: UUID | None = Field(default=None, description="UUID СЃСѓС‰РЅРѕСЃС‚Рё ERP")
    message: str | None = Field(default=None, description="РЎРѕРѕР±С‰РµРЅРёРµ")
    error: str | None = Field(default=None, description="РћС€РёР±РєР°")

    model_config = ConfigDict(from_attributes=True)
