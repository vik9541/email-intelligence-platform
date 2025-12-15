"""
Unit Tests for Response Generator and Templates.

Tests:
- Language detection (RU/EN)
- Tone detection
- Signature extraction
- Template rendering
- Response generation
"""

import pytest
from datetime import datetime

from app.services.response_templates import (
    ResponseTemplateService, ResponseLanguage, ResponseTone, EmailTemplate
)
from app.services.response_generator import (
    ResponseGenerator, LanguageDetector, ToneDetector, SignatureExtractor
)
from app.models.email_models import EmailDocument, EmailCategory, Classification


@pytest.fixture
def template_service():
    return ResponseTemplateService()


@pytest.fixture
def response_generator(template_service):
    return ResponseGenerator(template_service, ollama_client=None)


# ========================================
# TEST: Language Detection
# ========================================

def test_detect_russian():
    """Определить русский язык"""
    
    text = "Спасибо за ваше письмо. Мы получили ваш заказ и обработаем его."
    
    language = LanguageDetector.detect(text)
    
    assert language == ResponseLanguage.RUSSIAN


def test_detect_english():
    """Определить английский язык"""
    
    text = "Thank you for your email. We have received your order and will process it."
    
    language = LanguageDetector.detect(text)
    
    assert language == ResponseLanguage.ENGLISH


def test_detect_mixed_prefer_russian():
    """Mixed текст - предпочесть русский если его больше"""
    
    text = "Спасибо за письмо. Thank you for email. Ваше письмо получено."
    
    language = LanguageDetector.detect(text)
    
    assert language == ResponseLanguage.RUSSIAN


def test_detect_empty_text():
    """Пустой текст - вернуть английский по умолчанию"""
    
    language = LanguageDetector.detect("")
    
    assert language == ResponseLanguage.ENGLISH


# ========================================
# TEST: Tone Detection
# ========================================

def test_detect_urgent_tone():
    """Определить срочный tone"""
    
    subject = "URGENT: Critical Issue"
    body = "This needs to be fixed immediately!"
    
    tone = ToneDetector.detect(subject, body)
    
    assert tone == ResponseTone.URGENT


def test_detect_friendly_tone():
    """Определить дружелюбный tone"""
    
    subject = "Thank you for your help"
    body = "We really appreciate your assistance!"
    
    tone = ToneDetector.detect(subject, body)
    
    assert tone == ResponseTone.FRIENDLY


def test_detect_professional_default():
    """Default professional tone"""
    
    subject = "Update"
    body = "Here is the information."
    
    tone = ToneDetector.detect(subject, body)
    
    assert tone == ResponseTone.PROFESSIONAL


def test_detect_formal_tone():
    """Определить официальный tone"""
    
    subject = "Formal Notice"
    body = "We hereby notify you officially about the changes."
    
    tone = ToneDetector.detect(subject, body)
    
    assert tone == ResponseTone.FORMAL


# ========================================
# TEST: Signature Extraction
# ========================================

def test_extract_signature_standard():
    """Извлечь стандартную подпись"""
    
    body = """Hello,

This is the email body.

--
John Smith
Company Name
john@example.com"""
    
    signature = SignatureExtractor.extract(body)
    
    assert signature is not None
    assert "John Smith" in signature


def test_extract_signature_russian():
    """Извлечь русскую подпись"""
    
    body = """Добрый день,

Текст письма.

С уважением,
Иван Петров
ООО Компания"""
    
    signature = SignatureExtractor.extract(body)
    
    assert signature is not None
    assert "Иван" in signature or "Петров" in signature


def test_extract_no_signature():
    """Письмо без подписи"""
    
    body = "Short email with no signature"
    
    signature = SignatureExtractor.extract(body)
    
    assert signature is None


# ========================================
# TEST: Template Rendering
# ========================================

def test_render_invoice_template(template_service):
    """Рендерить invoice шаблон"""
    
    template = template_service.get_template(
        "invoice",
        ResponseLanguage.RUSSIAN,
        ResponseTone.PROFESSIONAL
    )
    
    assert template is not None
    
    variables = {
        'name': 'Ivan Petrov',
        'invoice_number': 'INV-2024-001',
        'amount': '50000.00',
        'currency': 'RUB',
        'our_company': 'OOO MyCompany'
    }
    
    subject, body = template_service.render(template, variables)
    
    assert 'INV-2024-001' in subject
    assert 'Ivan Petrov' in body
    assert '50000.00' in body


def test_render_order_template(template_service):
    """Рендерить order шаблон"""
    
    template = template_service.get_template(
        "purchase_order",
        ResponseLanguage.ENGLISH,
        ResponseTone.PROFESSIONAL
    )
    
    assert template is not None
    
    variables = {
        'name': 'John',
        'order_number': 'PO-2024-001',
        'delivery_date': '2024-12-25',
        'our_company': 'MyCompany Ltd'
    }
    
    subject, body = template_service.render(template, variables)
    
    assert 'PO-2024-001' in subject
    assert 'John' in body


def test_render_missing_variables_filled(template_service):
    """Отсутствующие переменные заполняются placeholders"""
    
    template = template_service.get_template(
        "invoice",
        ResponseLanguage.RUSSIAN,
        ResponseTone.PROFESSIONAL
    )
    
    variables = {'name': 'Ivan'}  # Не все переменные
    
    # Should not raise, fills with placeholders
    subject, body = template_service.render(template, variables)
    
    assert subject is not None
    assert body is not None


# ========================================
# TEST: Template Selection
# ========================================

def test_get_template_exact_match(template_service):
    """Получить точно совпадающий шаблон"""
    
    template = template_service.get_template(
        "invoice",
        ResponseLanguage.RUSSIAN,
        ResponseTone.PROFESSIONAL
    )
    
    assert template is not None
    assert template.category == "invoice"
    assert template.language == ResponseLanguage.RUSSIAN
    assert template.tone == ResponseTone.PROFESSIONAL


def test_get_template_fallback_tone(template_service):
    """Fallback на professional tone если нет нужного"""
    
    # Request friendly tone which might not exist for invoice
    template = template_service.get_template(
        "invoice",
        ResponseLanguage.RUSSIAN,
        ResponseTone.FRIENDLY
    )
    
    assert template is not None
    # Should fallback to professional
    assert template.tone == ResponseTone.PROFESSIONAL


def test_list_templates_all(template_service):
    """Получить все шаблоны"""
    
    templates = template_service.list_templates()
    
    assert len(templates) > 0
    assert all(t.is_active for t in templates)


def test_list_templates_by_category(template_service):
    """Получить шаблоны по категории"""
    
    templates = template_service.list_templates(category="invoice")
    
    assert len(templates) > 0
    assert all(t.category == "invoice" for t in templates)


def test_template_service_stats(template_service):
    """Проверить статистику шаблонов"""
    
    stats = template_service.get_stats()
    
    assert 'total_templates' in stats
    assert 'active_templates' in stats
    assert 'by_category' in stats
    assert 'by_language' in stats
    assert stats['total_templates'] > 0


# ========================================
# TEST: Response Generation
# ========================================

@pytest.mark.asyncio
async def test_generate_from_template(response_generator):
    """Сгенерировать ответ из шаблона"""
    
    email = EmailDocument(
        message_id="test-1",
        from_email="vendor@example.com",
        to_email="buyer@example.com",
        subject="Invoice INV-2024-001",
        body_text="Please see attached invoice.",
        size_bytes=100,
        received_at=datetime.utcnow()
    )
    
    classification = Classification(
        category=EmailCategory.INVOICE,
        confidence=0.95,  # High confidence - should use template
        reasoning="Clear invoice"
    )
    
    response = await response_generator.generate(email, classification)
    
    assert response is not None
    assert response.generated_from == "template"
    assert response.subject is not None
    assert response.body is not None
    assert len(response.body) > 0


@pytest.mark.asyncio
async def test_generate_fallback_low_confidence(response_generator):
    """Сгенерировать fallback ответ при низкой confidence"""
    
    email = EmailDocument(
        message_id="test-2",
        from_email="sender@example.com",
        to_email="receiver@example.com",
        subject="Random email",
        body_text="Some text",
        size_bytes=50,
        received_at=datetime.utcnow()
    )
    
    classification = Classification(
        category=EmailCategory.OTHER,
        confidence=0.50,  # Low confidence
        reasoning="Unclear category"
    )
    
    response = await response_generator.generate(email, classification)
    
    assert response is not None
    assert response.subject is not None
    assert response.requires_approval == True


@pytest.mark.asyncio
async def test_generate_stats_updated(response_generator):
    """Проверить обновление статистики"""
    
    email = EmailDocument(
        message_id="test-3",
        from_email="test@example.com",
        to_email="receiver@example.com",
        subject="Test",
        body_text="Test body",
        size_bytes=50,
        received_at=datetime.utcnow()
    )
    
    classification = Classification(
        category=EmailCategory.SUPPORT,
        confidence=0.90,
        reasoning="Support request"
    )
    
    initial_count = response_generator.stats['total_generated']
    
    await response_generator.generate(email, classification)
    
    stats = response_generator.get_stats()
    
    assert stats['total_generated'] == initial_count + 1
    assert stats['from_template'] > 0
