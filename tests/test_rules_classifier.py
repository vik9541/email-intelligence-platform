"""
Unit Tests for Rules-Based Classifier
Tests: keyword matching, pattern matching, sender matching, performance
"""

import pytest
from datetime import datetime
from app.services.rules_loader import RulesConfiguration
from app.services.rules_classifier import RulesEngine
from app.models.email_models import EmailDocument, EmailCategory


@pytest.fixture
def rules_config():
    """Загрузить конфигурацию правил"""
    return RulesConfiguration("config/classification_rules.yaml")


@pytest.fixture
def rules_engine(rules_config):
    """Создать RulesEngine с конфигурацией"""
    return RulesEngine(rules_config)


# ==============================================================================
# TEST: Invoice Detection
# ==============================================================================

def test_classify_invoice_with_keywords(rules_engine):
    """Найти счет по keywords"""
    email = EmailDocument(
        message_id="test-invoice-1",
        from_email="vendor@example.com",
        to_email="buyer@company.com",
        subject="Invoice INV-2024-001 for December",
        body_text="Please see attached invoice for amount $5000. Payment due within 30 days.",
        size_bytes=1024,
        received_at=datetime.utcnow()
    )
    
    result = rules_engine.classify(email)
    
    assert result is not None, "Classification should not be None"
    assert result.category == EmailCategory.INVOICE, f"Expected INVOICE, got {result.category}"
    assert result.confidence > 0.75, f"Confidence {result.confidence} should be > 0.75"
    assert result.reasoning is not None


def test_classify_invoice_with_patterns(rules_engine):
    """Найти счет по regex patterns"""
    email = EmailDocument(
        message_id="test-invoice-2",
        from_email="billing@example.com",
        to_email="buyer@company.com",
        subject="Your invoice INV-2024-0098",
        body_text="Total amount: €1500. VAT 20%. Reference: INV-2024-0098",
        size_bytes=800,
        received_at=datetime.utcnow()
    )
    
    result = rules_engine.classify(email)
    
    assert result is not None
    assert result.category == EmailCategory.INVOICE
    assert result.confidence > 0.70


def test_classify_invoice_with_sender_pattern(rules_engine):
    """Найти счет по sender domain"""
    email = EmailDocument(
        message_id="test-invoice-3",
        from_email="accounts@billing-company.com",
        to_email="buyer@company.com",
        subject="Monthly invoice",
        body_text="Please find attached",
        size_bytes=600,
        received_at=datetime.utcnow()
    )
    
    result = rules_engine.classify(email)
    
    assert result is not None
    assert result.category == EmailCategory.INVOICE


def test_classify_invoice_exclude_keywords(rules_engine):
    """Исключить fake invoices через exclude_keywords"""
    email = EmailDocument(
        message_id="test-invoice-exclude",
        from_email="spammer@example.com",
        to_email="buyer@company.com",
        subject="Free Invoice template download",
        body_text="Download our invoice template sample now!",
        size_bytes=500,
        received_at=datetime.utcnow()
    )
    
    result = rules_engine.classify(email)
    
    # Не должен классифицировать как счет (из-за "invoice template")
    if result and result.category == EmailCategory.INVOICE:
        assert result.confidence < 0.5, "Fake invoice should have low confidence"


def test_classify_invoice_russian(rules_engine):
    """Найти русский счет"""
    email = EmailDocument(
        message_id="test-invoice-ru",
        from_email="finance@company.ru",
        to_email="buyer@client.ru",
        subject="Счет № 12345 от 15.12.2025",
        body_text="К оплате: 150 000 ₽. НДС 20%. ИНН: 1234567890",
        size_bytes=900,
        received_at=datetime.utcnow()
    )
    
    result = rules_engine.classify(email)
    
    assert result is not None
    assert result.category == EmailCategory.INVOICE
    assert result.confidence > 0.75


# ==============================================================================
# TEST: Purchase Order Detection
# ==============================================================================

def test_classify_purchase_order(rules_engine):
    """Найти заказ"""
    email = EmailDocument(
        message_id="test-po-1",
        from_email="procurement@supplier.com",
        to_email="vendor@company.com",
        subject="Purchase Order PO-2024-001",
        body_text="Item: Widget ABC, SKU-ABC123, Qty: 100 units, Unit price: $50",
        size_bytes=1200,
        received_at=datetime.utcnow()
    )
    
    result = rules_engine.classify(email)
    
    assert result is not None
    assert result.category == EmailCategory.PURCHASE_ORDER
    assert result.confidence > 0.70


def test_classify_purchase_order_russian(rules_engine):
    """Найти русский заказ"""
    email = EmailDocument(
        message_id="test-po-ru",
        from_email="zakupki@supplier.ru",
        to_email="vendor@company.ru",
        subject="Заказ № 5678",
        body_text="Наименование: Товар А, Артикул: ABC-123, Количество: 50 шт",
        size_bytes=1000,
        received_at=datetime.utcnow()
    )
    
    result = rules_engine.classify(email)
    
    assert result is not None
    assert result.category == EmailCategory.PURCHASE_ORDER


# ==============================================================================
# TEST: Support Ticket Detection
# ==============================================================================

def test_classify_support_ticket(rules_engine):
    """Найти тикет поддержки"""
    email = EmailDocument(
        message_id="test-support-1",
        from_email="customer@example.com",
        to_email="support@company.com",
        subject="URGENT: Cannot access my account",
        body_text="Error code: 403. The system is not working. Please help ASAP!",
        size_bytes=600,
        received_at=datetime.utcnow()
    )
    
    result = rules_engine.classify(email)
    
    assert result is not None
    assert result.category == EmailCategory.SUPPORT
    assert result.confidence > 0.70


def test_classify_support_with_ticket_number(rules_engine):
    """Найти тикет по номеру"""
    email = EmailDocument(
        message_id="test-support-2",
        from_email="user@example.com",
        to_email="help@company.com",
        subject="RE: TICKET-123456",
        body_text="Still having the same problem",
        size_bytes=400,
        received_at=datetime.utcnow()
    )
    
    result = rules_engine.classify(email)
    
    assert result is not None
    assert result.category == EmailCategory.SUPPORT


# ==============================================================================
# TEST: Sales Quote Detection
# ==============================================================================

def test_classify_sales_quote(rules_engine):
    """Найти коммерческое предложение"""
    email = EmailDocument(
        message_id="test-sales-1",
        from_email="sales@company.com",
        to_email="prospect@example.com",
        subject="Special Quote for your business - QUOTE-2024-5000",
        body_text="We are pleased to offer you a 20% discount on our premium package.",
        size_bytes=900,
        received_at=datetime.utcnow()
    )
    
    result = rules_engine.classify(email)
    
    assert result is not None
    assert result.category == EmailCategory.SALES
    assert result.confidence > 0.65


def test_classify_sales_russian(rules_engine):
    """Найти русское КП"""
    email = EmailDocument(
        message_id="test-sales-ru",
        from_email="sales@company.ru",
        to_email="client@example.ru",
        subject="Коммерческое предложение № КП-2024-001",
        body_text="Предлагаем специальную скидку 15% на нашу продукцию",
        size_bytes=850,
        received_at=datetime.utcnow()
    )
    
    result = rules_engine.classify(email)
    
    assert result is not None
    assert result.category == EmailCategory.SALES


# ==============================================================================
# TEST: HR/Admin Detection
# ==============================================================================

def test_classify_hr_email(rules_engine):
    """Найти HR письмо"""
    email = EmailDocument(
        message_id="test-hr-1",
        from_email="hr@company.com",
        to_email="employee@company.com",
        subject="Employee benefits and training program update",
        body_text="New vacation policy effective next month. Salary review in Q1.",
        size_bytes=750,
        received_at=datetime.utcnow()
    )
    
    result = rules_engine.classify(email)
    
    assert result is not None
    assert result.category == EmailCategory.HR


def test_classify_hr_russian(rules_engine):
    """Найти русское HR письмо"""
    email = EmailDocument(
        message_id="test-hr-ru",
        from_email="kadry@company.ru",
        to_email="employee@company.ru",
        subject="Информация об отпусках и обучении",
        body_text="График отпусков на 2025 год. Тренинг для сотрудников.",
        size_bytes=700,
        received_at=datetime.utcnow()
    )
    
    result = rules_engine.classify(email)
    
    assert result is not None
    assert result.category == EmailCategory.HR


# ==============================================================================
# TEST: Newsletter Detection
# ==============================================================================

def test_classify_newsletter(rules_engine):
    """Найти рассылку"""
    email = EmailDocument(
        message_id="test-newsletter-1",
        from_email="noreply@newsletter.com",
        to_email="subscriber@example.com",
        subject="Weekly Newsletter - Tech Updates",
        body_text="Click here to unsubscribe from this mailing list",
        size_bytes=2000,
        received_at=datetime.utcnow()
    )
    
    result = rules_engine.classify(email)
    
    assert result is not None
    assert result.category == EmailCategory.NEWSLETTER


# ==============================================================================
# TEST: Performance
# ==============================================================================

def test_classify_performance_latency(rules_engine):
    """Проверить что классификация < 100ms"""
    import time
    
    email = EmailDocument(
        message_id="test-performance",
        from_email="vendor@example.com",
        to_email="buyer@company.com",
        subject="Invoice INV-2024-999 - Payment Required",
        body_text="Please see attached invoice for $10,000. Payment due in 14 days.",
        size_bytes=1024,
        received_at=datetime.utcnow()
    )
    
    start = time.time()
    result = rules_engine.classify(email)
    elapsed_ms = (time.time() - start) * 1000
    
    assert elapsed_ms < 100, f"Classification took {elapsed_ms:.1f}ms (> 100ms target)"
    assert result is not None


def test_classify_batch_performance(rules_engine):
    """Проверить batch performance"""
    import time
    
    # Создать 50 тестовых писем
    emails = [
        EmailDocument(
            message_id=f"test-batch-{i}",
            from_email=f"sender{i}@example.com",
            to_email="receiver@company.com",
            subject=f"Invoice INV-2024-{i:04d}",
            body_text=f"Test invoice number {i}",
            size_bytes=1000,
            received_at=datetime.utcnow()
        )
        for i in range(50)
    ]
    
    start = time.time()
    
    results = [rules_engine.classify(email) for email in emails]
    
    total_time = time.time() - start
    avg_time_ms = (total_time / len(emails)) * 1000
    
    assert avg_time_ms < 100, f"Avg time {avg_time_ms:.1f}ms (> 100ms target)"
    assert all(r is not None for r in results), "All emails should be classified"


# ==============================================================================
# TEST: Statistics
# ==============================================================================

def test_get_classification_statistics(rules_engine):
    """Проверить сбор статистики"""
    # Классифицировать несколько писем разных категорий
    emails = [
        # 3 invoices
        EmailDocument(
            message_id="stats-inv-1",
            from_email="billing@example.com",
            to_email="buyer@company.com",
            subject="Invoice INV-001",
            body_text="Amount: $1000",
            size_bytes=500,
            received_at=datetime.utcnow()
        ),
        EmailDocument(
            message_id="stats-inv-2",
            from_email="accounts@example.com",
            to_email="buyer@company.com",
            subject="Invoice INV-002",
            body_text="Amount: $2000",
            size_bytes=500,
            received_at=datetime.utcnow()
        ),
        EmailDocument(
            message_id="stats-inv-3",
            from_email="finance@example.com",
            to_email="buyer@company.com",
            subject="Invoice INV-003",
            body_text="Amount: $3000",
            size_bytes=500,
            received_at=datetime.utcnow()
        ),
        # 2 support tickets
        EmailDocument(
            message_id="stats-support-1",
            from_email="customer@example.com",
            to_email="support@company.com",
            subject="URGENT: System error",
            body_text="Error code 500",
            size_bytes=400,
            received_at=datetime.utcnow()
        ),
        EmailDocument(
            message_id="stats-support-2",
            from_email="user@example.com",
            to_email="help@company.com",
            subject="Bug report",
            body_text="Application crash",
            size_bytes=400,
            received_at=datetime.utcnow()
        ),
    ]
    
    for email in emails:
        rules_engine.classify(email)
    
    stats = rules_engine.get_stats()
    
    assert stats['total_classified'] == 5
    assert 'invoice' in stats['categories']
    assert 'support' in stats['categories']
    assert stats['categories']['invoice'] == 3
    assert stats['categories']['support'] == 2
    assert 'avg_processing_time_ms' in stats
    assert stats['avg_processing_time_ms'] < 100


def test_reset_statistics(rules_engine):
    """Проверить сброс статистики"""
    # Классифицировать письмо
    email = EmailDocument(
        message_id="test-reset",
        from_email="test@example.com",
        to_email="receiver@company.com",
        subject="Invoice INV-123",
        body_text="Test",
        size_bytes=100,
        received_at=datetime.utcnow()
    )
    
    rules_engine.classify(email)
    
    stats_before = rules_engine.get_stats()
    assert stats_before['total_classified'] == 1
    
    # Сбросить
    rules_engine.reset_stats()
    
    stats_after = rules_engine.get_stats()
    assert stats_after['total_classified'] == 0
    assert len(stats_after['categories']) == 0


# ==============================================================================
# TEST: Edge Cases
# ==============================================================================

def test_classify_empty_email(rules_engine):
    """Классификация пустого письма"""
    email = EmailDocument(
        message_id="test-empty",
        from_email="sender@example.com",
        to_email="receiver@company.com",
        subject="",
        body_text="",
        size_bytes=0,
        received_at=datetime.utcnow()
    )
    
    result = rules_engine.classify(email)
    
    # Может вернуть None или низкий confidence
    if result:
        assert result.confidence < 0.5


def test_classify_no_subject(rules_engine):
    """Классификация письма без subject"""
    email = EmailDocument(
        message_id="test-no-subject",
        from_email="billing@example.com",
        to_email="buyer@company.com",
        subject="",
        body_text="Invoice INV-2024-001 for $5000",
        size_bytes=500,
        received_at=datetime.utcnow()
    )
    
    result = rules_engine.classify(email)
    
    # Должен классифицировать по body
    assert result is not None
    assert result.category == EmailCategory.INVOICE


def test_classify_multiple_category_matches(rules_engine):
    """Письмо подходит под несколько категорий"""
    email = EmailDocument(
        message_id="test-multi",
        from_email="support@billing-company.com",
        to_email="customer@example.com",
        subject="Invoice INV-001 - Support Ticket TICKET-123",
        body_text="Your invoice has an error. Please help fix it urgently.",
        size_bytes=600,
        received_at=datetime.utcnow()
    )
    
    result = rules_engine.classify(email)
    
    # Должен выбрать одну категорию с наибольшим confidence
    assert result is not None
    assert result.category in [EmailCategory.INVOICE, EmailCategory.SUPPORT]
