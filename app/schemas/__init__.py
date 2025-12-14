"""
Инициализация пакета схем.
"""

from app.schemas.erp_schemas import (
    ActionResult,
    ActionStatus,
    EmailActionResult,
    ERPOrder,
    OrderItem,
    OrderStatus,
)

__all__ = [
    "ActionResult",
    "ActionStatus",
    "EmailActionResult",
    "ERPOrder",
    "OrderItem",
    "OrderStatus",
]
