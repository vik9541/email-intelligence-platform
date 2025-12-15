"""
Unit Tests for Invoice and Order Extractors.

Tests:
- Invoice extraction (Russian + English)
- Order extraction (Russian + English)
- Confidence calculation
- Error handling
"""

import pytest
from datetime import datetime
from decimal import Decimal

from app.services.invoice_extractor import InvoiceExtractor, CurrencyType, PaymentTerms
from app.services.order_extractor import OrderExtractor, OrderPriority


@pytest.fixture
def invoice_extractor():
    return InvoiceExtractor()


@pytest.fixture
def order_extractor():
    return OrderExtractor()


# ========================================
# TEST: Invoice Extraction - Russian
# ========================================

def test_extract_invoice_ru(invoice_extractor):
    """Извлечь счет из русского текста"""
    
    subject = "Счет № ИНВ-2024-001"
    body = """
    Счет от 15.12.2024
    
    Сумма: 50000.00 ₽
    НДС (18%): 9000.00 ₽
    
    Итого к оплате: 59000.00 ₽
    
    Оплата: Net 30
    """
    
    extracted = invoice_extractor.extract(
        subject, body, "vendor@example.com", "ООО Поставщик"
    )
    
    assert extracted is not None
    assert extracted.invoice_number == "ИНВ-2024-001"
    assert extracted.total_amount == Decimal("59000.00")
    assert extracted.currency == CurrencyType.RUB
    assert "vendor@example.com" in extracted.vendor_email


def test_extract_invoice_en(invoice_extractor):
    """Извлечь счет из английского текста"""
    
    subject = "Invoice INV-2024-0001"
    body = """
    Invoice Date: 15.12.2024
    
    Total: $5000.00
    VAT (20%): $1000.00
    Amount Due: $6000.00
    
    Payment Terms: Net 60
    """
    
    extracted = invoice_extractor.extract(subject, body, "vendor@example.com")
    
    assert extracted is not None
    assert extracted.invoice_number == "INV-2024-0001"
    assert extracted.total_amount == Decimal("6000.00")
    assert extracted.currency == CurrencyType.USD
    assert extracted.payment_terms == PaymentTerms.NET_60


def test_extract_invoice_confidence(invoice_extractor):
    """Проверить confidence score"""
    
    subject = "Invoice INV-123"
    body = "Total: 1000.00 RUB\nНДС: 18%"
    
    extracted = invoice_extractor.extract(subject, body, "test@example.com")
    
    assert extracted is not None
    assert 0.0 <= extracted.confidence <= 1.0
    assert extracted.confidence >= 0.5  # Should have some keywords


def test_extract_invoice_no_data(invoice_extractor):
    """Обработать невалидный счет без данных"""
    
    subject = "Random email"
    body = "This is just a regular email with no invoice data"
    
    extracted = invoice_extractor.extract(subject, body, "test@example.com")
    
    # Должен вернуть None если не найден номер счета
    assert extracted is None


# ========================================
# TEST: Invoice VAT Calculation
# ========================================

def test_extract_vat_calculation(invoice_extractor):
    """Проверить расчет НДС"""
    
    subject = "Счет INV-VAT-001"
    body = """
    Итого: 11800.00 ₽
    НДС (18%)
    """
    
    extracted = invoice_extractor.extract(subject, body, "vendor@example.com")
    
    assert extracted is not None
    assert extracted.vat_rate == 18
    # VAT amount should be calculated from total
    expected_vat = (Decimal("11800.00") * Decimal(18)) / Decimal(118)
    assert abs(extracted.vat_amount - expected_vat) < Decimal("0.01")


def test_extract_due_date_calculation(invoice_extractor):
    """Проверить расчет срока оплаты"""
    
    subject = "Invoice INV-DUE-001"
    body = """
    Invoice Date: 01.12.2024
    Total: 1000.00 RUB
    Payment Terms: Net 30
    """
    
    extracted = invoice_extractor.extract(subject, body, "vendor@example.com")
    
    assert extracted is not None
    assert extracted.payment_terms == PaymentTerms.NET_30
    
    # Due date should be 30 days after invoice date
    expected_due = extracted.invoice_date
    days_diff = (extracted.due_date - expected_due).days
    assert days_diff == 30


# ========================================
# TEST: Order Extraction - Russian
# ========================================

def test_extract_order_ru(order_extractor):
    """Извлечь заказ из русского текста"""
    
    subject = "Заказ PO-2024-001"
    body = """
    Заказ на:
    
    SKU: ABC123 - Кол-во: 100, Цена: 1000.00 ₽
    SKU: DEF456 - Кол-во: 50, Цена: 2000.00 ₽
    
    Доставка: 25.12.2024
    Срочно!
    """
    
    extracted = order_extractor.extract(subject, body, "customer@example.com")
    
    assert extracted is not None
    assert extracted.order_number == "PO-2024-001"
    assert len(extracted.line_items) == 2
    assert extracted.priority == OrderPriority.URGENT


def test_extract_order_line_items(order_extractor):
    """Проверить извлечение line items"""
    
    subject = "Order PO-ITEMS-001"
    body = """
    SKU: ITEM-001, Qty: 10, Price: 100.00
    SKU: ITEM-002, Qty: 5, Price: 200.00
    SKU: ITEM-003, Qty: 20, Price: 50.00
    """
    
    extracted = order_extractor.extract(subject, body, "customer@example.com")
    
    assert extracted is not None
    assert len(extracted.line_items) == 3
    
    # Check first item
    item1 = extracted.line_items[0]
    assert item1.sku == "ITEM-001"
    assert item1.quantity == 10
    assert item1.unit_price == Decimal("100.00")
    assert item1.total == Decimal("1000.00")


def test_extract_order_priority(order_extractor):
    """Проверить определение приоритета"""
    
    # Test URGENT
    extracted = order_extractor.extract(
        "URGENT Order PO-001",
        "Need ASAP!",
        "customer@example.com"
    )
    assert extracted is not None
    assert extracted.priority == OrderPriority.URGENT
    
    # Test HIGH
    extracted = order_extractor.extract(
        "High Priority Order PO-002",
        "Important",
        "customer@example.com"
    )
    assert extracted is not None
    assert extracted.priority == OrderPriority.HIGH
    
    # Test NORMAL (default)
    extracted = order_extractor.extract(
        "Order PO-003",
        "Regular order",
        "customer@example.com"
    )
    assert extracted is not None
    assert extracted.priority == OrderPriority.NORMAL


# ========================================
# TEST: Error Handling
# ========================================

def test_extract_invalid_order(order_extractor):
    """Обработать невалидный заказ"""
    
    subject = "Random email"
    body = "This is just a regular email with no order data"
    
    extracted = order_extractor.extract(subject, body, "test@example.com")
    
    # Должен вернуть None если не найден номер заказа
    assert extracted is None


def test_extract_invoice_with_notes(invoice_extractor):
    """Проверить сбор заметок при проблемах"""
    
    subject = "Draft Invoice INV-DRAFT-001"
    body = "Total: 1000 RUB"
    
    extracted = invoice_extractor.extract(subject, body, "vendor@example.com")
    
    assert extracted is not None
    assert len(extracted.extraction_notes) > 0
    # Should have note about draft
    assert any("draft" in note.lower() for note in extracted.extraction_notes)


def test_extract_order_with_missing_price(order_extractor):
    """Проверить заметки при отсутствии цены"""
    
    subject = "Order PO-NOPRICE-001"
    body = """
    SKU: ITEM-001, Qty: 10
    """
    
    extracted = order_extractor.extract(subject, body, "customer@example.com")
    
    assert extracted is not None
    assert len(extracted.line_items) == 1
    # Should have note about missing price
    assert len(extracted.extraction_notes) > 0
    assert any("price" in note.lower() for note in extracted.extraction_notes)


# ========================================
# TEST: Currency Detection
# ========================================

def test_extract_invoice_currency_rub(invoice_extractor):
    """Определить валюту RUB"""
    
    extracted = invoice_extractor.extract(
        "Invoice INV-RUB",
        "Total: 1000 ₽",
        "vendor@example.com"
    )
    
    assert extracted is not None
    assert extracted.currency == CurrencyType.RUB


def test_extract_invoice_currency_usd(invoice_extractor):
    """Определить валюту USD"""
    
    extracted = invoice_extractor.extract(
        "Invoice INV-USD",
        "Total: $1000.00",
        "vendor@example.com"
    )
    
    assert extracted is not None
    assert extracted.currency == CurrencyType.USD


def test_extract_invoice_currency_eur(invoice_extractor):
    """Определить валюту EUR"""
    
    extracted = invoice_extractor.extract(
        "Invoice INV-EUR",
        "Total: €1000.00",
        "vendor@example.com"
    )
    
    assert extracted is not None
    assert extracted.currency == CurrencyType.EUR
