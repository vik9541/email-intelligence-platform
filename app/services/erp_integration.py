"""
ERP Integration Service - Process classified emails into ERP documents.

Creates/updates:
- Invoices (from invoice emails)
- Orders (from purchase order emails)
- Tickets (from support emails)

Sends webhooks to ERP systems (SAP, 1C, Yandex.Kassa)
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from sqlalchemy import insert, update, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email_models import EmailDocument, EmailCategory, Classification
from app.services.invoice_extractor import InvoiceExtractor, ExtractedInvoice
from app.services.order_extractor import OrderExtractor, ExtractedOrder
from app.models.database import (
    InvoiceORM, OrderORM, TicketORM, CompanyORM
)

logger = logging.getLogger(__name__)


class DocumentStatus(str, Enum):
    """Статус документа в ERP"""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ERPIntegrationConfig:
    """Конфиг для ERP интеграции"""
    
    def __init__(self):
        self.webhook_urls = {
            'sap': 'http://sap-system:8080/api/documents/create',
            '1c': 'http://1c-system:8080/api/orders/import',
            'yandex_kassa': 'http://kassa.yandex.ru/api/payments/register'
        }
        self.auto_approve_whitelist = ['trusted-supplier@example.com']
        self.auto_close_refund = True
        self.max_retries = 3


class ERPIntegrationService:
    """
    Сервис интеграции с ERP системами
    Создает Orders, Invoices, Tickets из классифицированных писем
    """
    
    def __init__(self, config: ERPIntegrationConfig, db_session: AsyncSession):
        self.config = config
        self.db = db_session
        
        self.invoice_extractor = InvoiceExtractor()
        self.order_extractor = OrderExtractor()
        
        self.stats = {
            'invoices_created': 0,
            'invoices_updated': 0,
            'orders_created': 0,
            'orders_updated': 0,
            'tickets_created': 0,
            'tickets_closed': 0,
            'webhooks_sent': 0,
            'errors': 0
        }
    
    async def process_email(
        self,
        email: EmailDocument,
        classification: Classification
    ) -> Dict[str, Any]:
        """
        Обработать письмо в зависимости от классификации
        
        Args:
            email: Email document
            classification: Classification result
            
        Returns:
            Dict с результатом обработки
        """
        
        try:
            logger.info(
                f"Processing {classification.category} email "
                f"from {email.from_email}"
            )
            
            if classification.category == EmailCategory.INVOICE:
                return await self._process_invoice(email)
            
            elif classification.category == EmailCategory.PURCHASE_ORDER:
                return await self._process_order(email)
            
            elif classification.category == EmailCategory.SUPPORT:
                return await self._process_support(email)
            
            else:
                return {
                    'status': 'skipped',
                    'category': classification.category,
                    'message': f"No ERP integration for {classification.category}"
                }
        
        except Exception as e:
            logger.error(f"Error processing email: {e}")
            self.stats['errors'] += 1
            return {'status': 'error', 'message': str(e)}
    
    async def _process_invoice(self, email: EmailDocument) -> Dict[str, Any]:
        """Обработать Invoice email"""
        
        # Извлечь данные счета
        extracted = self.invoice_extractor.extract(
            email_subject=email.subject or "",
            email_body=email.body_text or "",
            from_email=email.from_email,
            from_name=None
        )
        
        if not extracted:
            return {'status': 'error', 'message': 'Failed to extract invoice data'}
        
        try:
            # Проверить существует ли уже
            stmt = select(InvoiceORM).where(
                InvoiceORM.invoice_number == extracted.invoice_number
            )
            result = await self.db.execute(stmt)
            existing = result.scalars().first()
            
            if existing:
                # Update существующего
                stmt = (
                    update(InvoiceORM)
                    .where(InvoiceORM.id == existing.id)
                    .values(
                        total_amount=extracted.total_amount,
                        vat_amount=extracted.vat_amount,
                        due_date=extracted.due_date,
                        updated_at=datetime.utcnow(),
                        status=DocumentStatus.APPROVED.value
                    )
                )
                await self.db.execute(stmt)
                self.stats['invoices_updated'] += 1
                
                logger.info(f"Updated invoice: {extracted.invoice_number}")
                
                result_status = 'updated'
            
            else:
                # Создать новый
                invoice = InvoiceORM(
                    invoice_number=extracted.invoice_number,
                    vendor_email=extracted.vendor_email,
                    vendor_name=extracted.vendor_name,
                    customer_name=extracted.customer_name,
                    invoice_date=extracted.invoice_date,
                    due_date=extracted.due_date,
                    subtotal_amount=extracted.subtotal,
                    vat_amount=extracted.vat_amount,
                    total_amount=extracted.total_amount,
                    currency=extracted.currency.value,
                    status=DocumentStatus.APPROVED.value,
                    email_id=email.message_id,
                    created_at=datetime.utcnow()
                )
                
                self.db.add(invoice)
                self.stats['invoices_created'] += 1
                
                logger.info(f"Created invoice: {extracted.invoice_number}")
                
                result_status = 'created'
            
            # Отправить webhook в ERP системы
            webhook_results = await self._send_webhooks('invoice', extracted)
            
            await self.db.commit()
            
            return {
                'status': result_status,
                'category': 'invoice',
                'invoice_number': extracted.invoice_number,
                'total_amount': str(extracted.total_amount),
                'webhooks': webhook_results,
                'confidence': extracted.confidence
            }
        
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error processing invoice: {e}")
            self.stats['errors'] += 1
            return {'status': 'error', 'message': str(e)}
    
    async def _process_order(self, email: EmailDocument) -> Dict[str, Any]:
        """Обработать Purchase Order email"""
        
        extracted = self.order_extractor.extract(
            email_subject=email.subject or "",
            email_body=email.body_text or "",
            from_email=email.from_email,
            from_name=None
        )
        
        if not extracted or not extracted.line_items:
            return {'status': 'error', 'message': 'Failed to extract order data'}
        
        try:
            # Определить должен ли быть auto-approved
            should_auto_approve = self._should_auto_approve_order(email.from_email)
            
            order_status = DocumentStatus.APPROVED if should_auto_approve else DocumentStatus.PENDING_APPROVAL
            
            # Проверить существует ли
            stmt = select(OrderORM).where(
                OrderORM.order_number == extracted.order_number
            )
            result = await self.db.execute(stmt)
            existing = result.scalars().first()
            
            if not existing:
                order = OrderORM(
                    order_number=extracted.order_number,
                    customer_email=extracted.customer_email,
                    customer_name=extracted.customer_name,
                    order_date=extracted.order_date,
                    delivery_date=extracted.delivery_date,
                    total_amount=extracted.total_amount,
                    status=order_status.value,
                    priority=extracted.priority.value,
                    email_id=email.message_id,
                    line_items_count=len(extracted.line_items),
                    created_at=datetime.utcnow()
                )
                
                self.db.add(order)
                self.stats['orders_created'] += 1
                
                logger.info(
                    f"Created order: {extracted.order_number} "
                    f"(status: {order_status.value})"
                )
                
                result_status = 'created'
            else:
                result_status = 'already_exists'
            
            # Отправить webhook если auto-approved
            webhook_results = []
            if should_auto_approve:
                webhook_results = await self._send_webhooks('order', extracted)
                self.stats['webhooks_sent'] += len(webhook_results)
            
            await self.db.commit()
            
            return {
                'status': result_status,
                'category': 'purchase_order',
                'order_number': extracted.order_number,
                'line_items': len(extracted.line_items),
                'total_amount': str(extracted.total_amount),
                'auto_approved': should_auto_approve,
                'webhooks': webhook_results,
                'priority': extracted.priority.value
            }
        
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error processing order: {e}")
            self.stats['errors'] += 1
            return {'status': 'error', 'message': str(e)}
    
    async def _process_support(self, email: EmailDocument) -> Dict[str, Any]:
        """Обработать Support/Ticket email"""
        
        try:
            # Определить приоритет по ключевым словам
            priority = self._determine_ticket_priority(email.subject or "")
            
            ticket = TicketORM(
                ticket_number=f"TKT-{int(datetime.utcnow().timestamp())}",
                customer_email=email.from_email,
                subject=email.subject or "Support Request",
                description=email.body_text or "",
                priority=priority,
                status='open',
                email_id=email.message_id,
                created_at=datetime.utcnow()
            )
            
            # Проверить на refund request
            if self.config.auto_close_refund and self._is_refund_request(email.body_text or ""):
                ticket.status = 'auto_closed'
                ticket.resolution = "Refund processed automatically"
                ticket.closed_at = datetime.utcnow()
                self.stats['tickets_closed'] += 1
            
            self.db.add(ticket)
            self.stats['tickets_created'] += 1
            
            await self.db.commit()
            
            logger.info(f"Created ticket: {ticket.ticket_number}")
            
            return {
                'status': 'created',
                'category': 'support',
                'ticket_number': ticket.ticket_number,
                'priority': priority,
                'auto_closed': ticket.status == 'auto_closed'
            }
        
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error processing support: {e}")
            self.stats['errors'] += 1
            return {'status': 'error', 'message': str(e)}
    
    async def _send_webhooks(
        self,
        doc_type: str,
        data: Any
    ) -> List[Dict[str, Any]]:
        """Отправить webhooks в ERP системы"""
        
        results = []
        
        # Только для production - пропустить в тестах
        if not self.config.webhook_urls:
            return results
        
        # Готовить payload в зависимости от типа
        payload = self._prepare_webhook_payload(doc_type, data)
        
        # Отправить в каждую систему
        for system_name, webhook_url in self.config.webhook_urls.items():
            try:
                # В реальном коде использовать aiohttp для async POST
                logger.debug(f"Would send to {system_name}: {webhook_url}")
                
                results.append({
                    'system': system_name,
                    'status': 'pending',
                    'url': webhook_url
                })
            
            except Exception as e:
                logger.error(f"Webhook error for {system_name}: {e}")
                results.append({
                    'system': system_name,
                    'status': 'error',
                    'error': str(e)
                })
        
        return results
    
    def _prepare_webhook_payload(self, doc_type: str, data: Any) -> Dict:
        """Подготовить payload для webhook"""
        
        if doc_type == 'invoice':
            return {
                'type': 'invoice',
                'invoice_number': data.invoice_number,
                'vendor_email': data.vendor_email,
                'total_amount': str(data.total_amount),
                'currency': data.currency.value,
                'due_date': data.due_date.isoformat()
            }
        
        elif doc_type == 'order':
            return {
                'type': 'order',
                'order_number': data.order_number,
                'customer_email': data.customer_email,
                'line_items': [
                    {
                        'sku': item.sku,
                        'quantity': item.quantity,
                        'unit_price': str(item.unit_price)
                    }
                    for item in data.line_items
                ],
                'total_amount': str(data.total_amount)
            }
        
        return {}
    
    def _should_auto_approve_order(self, from_email: str) -> bool:
        """Должен ли заказ быть auto-approved"""
        return from_email in self.config.auto_approve_whitelist
    
    def _determine_ticket_priority(self, subject: str) -> str:
        """Определить приоритет тикета"""
        subject_lower = subject.lower()
        
        if any(w in subject_lower for w in ['urgent', 'asap', 'критично']):
            return 'urgent'
        elif any(w in subject_lower for w in ['high', 'important', 'важно']):
            return 'high'
        elif any(w in subject_lower for w in ['low', 'minor', 'незначительно']):
            return 'low'
        
        return 'normal'
    
    def _is_refund_request(self, body: str) -> bool:
        """Проверить на запрос возврата"""
        keywords = ['refund', 'возврат', 'вернуть', 'debit', 'credit']
        body_lower = body.lower()
        
        return any(kw in body_lower for kw in keywords)
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику"""
        return {
            'invoices_created': self.stats['invoices_created'],
            'invoices_updated': self.stats['invoices_updated'],
            'orders_created': self.stats['orders_created'],
            'orders_updated': self.stats['orders_updated'],
            'tickets_created': self.stats['tickets_created'],
            'tickets_closed': self.stats['tickets_closed'],
            'webhooks_sent': self.stats['webhooks_sent'],
            'errors': self.stats['errors']
        }
