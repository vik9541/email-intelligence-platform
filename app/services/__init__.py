"""
Инициализация пакета сервисов.
"""

from app.services.erp_action_executor import ERPActionExecutor, create_email_action

__all__ = ["ERPActionExecutor", "create_email_action"]
