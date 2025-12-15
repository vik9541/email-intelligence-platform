"""
Integration Tests for ERP Integration Service.

Tests:
- Invoice processing (create/update)
- Order processing
- Support ticket creation
- Auto-approval logic
- Auto-close refund logic
- ERP statistics
"""

import pytest
from datetime import datetime
from httpx import AsyncClient
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import app
from app.models.email_models import EmailDocument, EmailCategory, Classification
from app.services.erp_integration import ERPIntegrationService, ERPIntegrationConfig


@pytest.fixture
def erp_config():
    """ERP configuration fixture"""
    config = ERPIntegrationConfig()
    config.webhook_urls = {}  # Disable webhooks for tests
    return config


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.add = MagicMock()
    return session


# ========================================
# TEST: Invoice Processing
# ========================================

@pytest.mark.asyncio
async def test_process_invoice_email(erp_config, mock_db_session):
    """Обработать Invoice email через ERP"""
    
    # Create ERP service
    erp = ERPIntegrationService(erp_config, mock_db_session)
    
    # Create email document
    email = EmailDocument(
        message_id="test-invoice-1",
        from_email="vendor@example.com",
        to_email="customer@example.com",
        subject="Invoice INV-2024-001",
        body_text="Total: 50000 RUB\nНДС (18%)",
        size_bytes=1000,
        received_at=datetime.utcnow()
    )
    
    # Create classification
    classification = Classification(
        category=EmailCategory.INVOICE,
        confidence=0.95,
        reasoning="Invoice detected"
    )
    
    # Mock DB to return no existing invoice
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = None
    mock_db_session.execute.return_value = mock_result
    
    # Process
    result = await erp.process_email(email, classification)
    
    assert result['status'] == 'created'
    assert result['category'] == 'invoice'
    assert 'invoice_number' in result
    assert erp.stats['invoices_created'] == 1


@pytest.mark.asyncio
async def test_process_invoice_update(erp_config, mock_db_session):
    """Обновить существующий invoice"""
    
    erp = ERPIntegrationService(erp_config, mock_db_session)
    
    email = EmailDocument(
        message_id="test-invoice-update",
        from_email="vendor@example.com",
        to_email="customer@example.com",
        subject="Updated Invoice INV-EXIST-001",
        body_text="Total: 60000 RUB",
        size_bytes=1000,
        received_at=datetime.utcnow()
    )
    
    classification = Classification(
        category=EmailCategory.INVOICE,
        confidence=0.95,
        reasoning="Invoice update"
    )
    
    # Mock DB to return existing invoice
    existing_invoice = MagicMock()
    existing_invoice.id = 1
    existing_invoice.invoice_number = "INV-EXIST-001"
    
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = existing_invoice
    mock_db_session.execute.return_value = mock_result
    
    # Process
    result = await erp.process_email(email, classification)
    
    assert result['status'] == 'updated'
    assert erp.stats['invoices_updated'] == 1


# ========================================
# TEST: Order Processing
# ========================================

@pytest.mark.asyncio
async def test_process_order_email(erp_config, mock_db_session):
    """Обработать Order email через ERP"""
    
    erp = ERPIntegrationService(erp_config, mock_db_session)
    
    email = EmailDocument(
        message_id="test-order-1",
        from_email="customer@example.com",
        to_email="supplier@example.com",
        subject="PO PO-2024-001",
        body_text="SKU: ABC123, Qty: 100, Price: 1000.00",
        size_bytes=1000,
        received_at=datetime.utcnow()
    )
    
    classification = Classification(
        category=EmailCategory.PURCHASE_ORDER,
        confidence=0.90,
        reasoning="Purchase order detected"
    )
    
    # Mock DB to return no existing order
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = None
    mock_db_session.execute.return_value = mock_result
    
    # Process
    result = await erp.process_email(email, classification)
    
    assert result['status'] == 'created'
    assert result['category'] == 'purchase_order'
    assert 'order_number' in result
    assert erp.stats['orders_created'] == 1


# ========================================
# TEST: Support Ticket Processing
# ========================================

@pytest.mark.asyncio
async def test_process_support_email(erp_config, mock_db_session):
    """Обработать Support email через ERP"""
    
    erp = ERPIntegrationService(erp_config, mock_db_session)
    
    email = EmailDocument(
        message_id="test-support-1",
        from_email="customer@example.com",
        to_email="support@example.com",
        subject="URGENT: Need help",
        body_text="I have a critical issue with the product",
        size_bytes=500,
        received_at=datetime.utcnow()
    )
    
    classification = Classification(
        category=EmailCategory.SUPPORT,
        confidence=0.88,
        reasoning="Support request"
    )
    
    # Process
    result = await erp.process_email(email, classification)
    
    assert result['status'] == 'created'
    assert result['category'] == 'support'
    assert result['priority'] == 'urgent'
    assert erp.stats['tickets_created'] == 1


@pytest.mark.asyncio
async def test_process_auto_refund(erp_config, mock_db_session):
    """Проверить auto-close для refund requests"""
    
    erp = ERPIntegrationService(erp_config, mock_db_session)
    
    email = EmailDocument(
        message_id="test-refund-1",
        from_email="customer@example.com",
        to_email="support@example.com",
        subject="Refund Request",
        body_text="I would like to request a refund for my order",
        size_bytes=500,
        received_at=datetime.utcnow()
    )
    
    classification = Classification(
        category=EmailCategory.SUPPORT,
        confidence=0.90,
        reasoning="Refund request"
    )
    
    # Process
    result = await erp.process_email(email, classification)
    
    assert result['status'] == 'created'
    assert result['auto_closed'] == True
    assert erp.stats['tickets_created'] == 1
    assert erp.stats['tickets_closed'] == 1


# ========================================
# TEST: ERP Statistics
# ========================================

@pytest.mark.asyncio
async def test_erp_stats(erp_config, mock_db_session):
    """Проверить статистику ERP обработки"""
    
    erp = ERPIntegrationService(erp_config, mock_db_session)
    
    # Process multiple emails
    erp.stats['invoices_created'] = 5
    erp.stats['orders_created'] = 3
    erp.stats['tickets_created'] = 2
    
    stats = erp.get_stats()
    
    assert stats['invoices_created'] == 5
    assert stats['orders_created'] == 3
    assert stats['tickets_created'] == 2
    assert 'errors' in stats


# ========================================
# TEST: Auto-Approval Logic
# ========================================

@pytest.mark.asyncio
async def test_auto_approve_trusted_supplier(erp_config, mock_db_session):
    """Проверить auto-approval для trusted suppliers"""
    
    erp_config.auto_approve_whitelist = ['trusted-supplier@example.com']
    erp = ERPIntegrationService(erp_config, mock_db_session)
    
    email = EmailDocument(
        message_id="test-trusted-1",
        from_email="trusted-supplier@example.com",
        to_email="customer@example.com",
        subject="Order PO-TRUSTED-001",
        body_text="SKU: ITEM-001, Qty: 10, Price: 100.00",
        size_bytes=500,
        received_at=datetime.utcnow()
    )
    
    classification = Classification(
        category=EmailCategory.PURCHASE_ORDER,
        confidence=0.95,
        reasoning="Order from trusted supplier"
    )
    
    # Mock DB
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = None
    mock_db_session.execute.return_value = mock_result
    
    # Process
    result = await erp.process_email(email, classification)
    
    assert result['status'] == 'created'
    assert result['auto_approved'] == True


# ========================================
# TEST: Error Handling
# ========================================

@pytest.mark.asyncio
async def test_process_invalid_category(erp_config, mock_db_session):
    """Обработать email с неподдерживаемой категорией"""
    
    erp = ERPIntegrationService(erp_config, mock_db_session)
    
    email = EmailDocument(
        message_id="test-invalid-1",
        from_email="sender@example.com",
        to_email="receiver@example.com",
        subject="Newsletter",
        body_text="Check out our latest products",
        size_bytes=500,
        received_at=datetime.utcnow()
    )
    
    classification = Classification(
        category=EmailCategory.OTHER,
        confidence=0.70,
        reasoning="Newsletter"
    )
    
    # Process
    result = await erp.process_email(email, classification)
    
    assert result['status'] == 'skipped'
    assert 'No ERP integration' in result['message']
