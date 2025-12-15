"""
Unit Tests for LLM-Based Classifier
Tests: Ollama integration, few-shot learning, JSON parsing, error handling
"""

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ollama_client import OllamaClient
from app.services.embedding_service import EmbeddingService
from app.services.llm_classifier import LLMClassifier
from app.models.email_models import EmailDocument, EmailCategory


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def ollama_client():
    """Mocked OllamaClient"""
    client = OllamaClient(host="http://localhost:11434", model="mistral:7b")
    client.session = AsyncMock()
    return client


@pytest.fixture
def embedding_service(ollama_client):
    """Mocked EmbeddingService"""
    service = EmbeddingService(db_service=MagicMock(), ollama_client=ollama_client)
    return service


@pytest.fixture
def llm_classifier(ollama_client, embedding_service):
    """LLMClassifier with mocked dependencies"""
    return LLMClassifier(ollama_client, embedding_service)


# ==============================================================================
# TEST: Invoice Classification
# ==============================================================================

@pytest.mark.asyncio
async def test_classify_invoice_llm(llm_classifier, ollama_client, embedding_service):
    """Классифицировать счет через LLM"""
    
    email = EmailDocument(
        message_id="test-llm-1",
        from_email="vendor@example.com",
        to_email="buyer@company.com",
        subject="Invoice INV-2024-001 for your purchase",
        body_text="Please find attached invoice for services rendered. Total amount: $5000. Payment due within 30 days.",
        size_bytes=1024,
        received_at=datetime.utcnow()
    )
    
    # Mock embedding service to return no similar emails
    embedding_service.find_similar_emails = AsyncMock(return_value=[])
    
    # Mock Ollama response
    mock_response = json.dumps({
        "category": "Invoice",
        "confidence": 0.98,
        "reasoning": "Clear invoice with amount and payment terms"
    })
    
    ollama_client.complete = AsyncMock(return_value=mock_response)
    
    result = await llm_classifier.classify(email, use_few_shot=False)
    
    assert result is not None
    assert result.category == EmailCategory.INVOICE
    assert result.confidence >= 0.90
    assert result.confidence <= 0.99
    assert "LLM:" in result.reasoning


@pytest.mark.asyncio
async def test_classify_with_few_shot(llm_classifier, ollama_client, embedding_service):
    """Классифицировать с few-shot learning"""
    
    email = EmailDocument(
        message_id="test-llm-2",
        from_email="supplier@example.com",
        to_email="buyer@company.com",
        subject="PO-2024-001 Purchase Request",
        body_text="Please provide quote for 100 units of product SKU-ABC",
        size_bytes=800,
        received_at=datetime.utcnow()
    )
    
    # Mock embedding service to return similar emails
    embedding_service.find_similar_emails = AsyncMock(return_value=[
        {
            'id': 1,
            'message_id': 'similar-1',
            'category': 'PO',
            'confidence': 0.95,
            'subject': 'Similar PO',
            'from_email': 'supplier2@example.com',
            'body_text': 'Purchase order example',
            'similarity': 0.85
        },
        {
            'id': 2,
            'message_id': 'similar-2',
            'category': 'PO',
            'confidence': 0.92,
            'subject': 'Another PO',
            'from_email': 'vendor@example.com',
            'body_text': 'Order details',
            'similarity': 0.78
        }
    ])
    
    # Mock Ollama response
    mock_response = json.dumps({
        "category": "PO",
        "confidence": 0.94,
        "reasoning": "Purchase order with SKU and quantity"
    })
    
    ollama_client.complete = AsyncMock(return_value=mock_response)
    
    result = await llm_classifier.classify(email, use_few_shot=True)
    
    assert result is not None
    assert result.category == EmailCategory.PURCHASE_ORDER
    assert result.confidence > 0.85


@pytest.mark.asyncio
async def test_classify_support_ticket(llm_classifier, ollama_client, embedding_service):
    """Классифицировать тикет поддержки"""
    
    email = EmailDocument(
        message_id="test-llm-3",
        from_email="customer@example.com",
        to_email="support@company.com",
        subject="URGENT: System is down, cannot access account",
        body_text="Our application is completely broken. Error code 500. This is critical. We need immediate help!",
        size_bytes=600,
        received_at=datetime.utcnow()
    )
    
    embedding_service.find_similar_emails = AsyncMock(return_value=[])
    
    mock_response = json.dumps({
        "category": "Support",
        "confidence": 0.96,
        "reasoning": "Critical issue with error code and urgency"
    })
    
    ollama_client.complete = AsyncMock(return_value=mock_response)
    
    result = await llm_classifier.classify(email, use_few_shot=False)
    
    assert result is not None
    assert result.category == EmailCategory.SUPPORT
    assert result.confidence > 0.90


@pytest.mark.asyncio
async def test_classify_sales_quote(llm_classifier, ollama_client, embedding_service):
    """Классифицировать коммерческое предложение"""
    
    email = EmailDocument(
        message_id="test-llm-4",
        from_email="sales@company.com",
        to_email="prospect@example.com",
        subject="Special Quote QUOTE-2024-5000 - 20% Discount",
        body_text="We are pleased to offer you a special 20% discount on our premium package. Deal expires soon!",
        size_bytes=900,
        received_at=datetime.utcnow()
    )
    
    embedding_service.find_similar_emails = AsyncMock(return_value=[])
    
    mock_response = json.dumps({
        "category": "Sales",
        "confidence": 0.91,
        "reasoning": "Quote with discount and deal terms"
    })
    
    ollama_client.complete = AsyncMock(return_value=mock_response)
    
    result = await llm_classifier.classify(email, use_few_shot=False)
    
    assert result is not None
    assert result.category == EmailCategory.SALES


@pytest.mark.asyncio
async def test_classify_hr_email(llm_classifier, ollama_client, embedding_service):
    """Классифицировать HR письмо"""
    
    email = EmailDocument(
        message_id="test-llm-5",
        from_email="hr@company.com",
        to_email="employee@company.com",
        subject="Employee Benefits Update - Training Program",
        body_text="New vacation policy effective next month. Salary review scheduled for Q1. Training opportunities available.",
        size_bytes=750,
        received_at=datetime.utcnow()
    )
    
    embedding_service.find_similar_emails = AsyncMock(return_value=[])
    
    mock_response = json.dumps({
        "category": "HR",
        "confidence": 0.88,
        "reasoning": "Employee benefits, training, salary topics"
    })
    
    ollama_client.complete = AsyncMock(return_value=mock_response)
    
    result = await llm_classifier.classify(email, use_few_shot=False)
    
    assert result is not None
    assert result.category == EmailCategory.HR


# ==============================================================================
# TEST: Response Parsing
# ==============================================================================

def test_parse_json_response(llm_classifier):
    """Парсить чистый JSON из LLM ответа"""
    
    email = EmailDocument(
        message_id="test-parse",
        from_email="test@example.com",
        to_email="receiver@company.com",
        subject="Test",
        body_text="Test",
        size_bytes=100,
        received_at=datetime.utcnow()
    )
    
    response = json.dumps({
        "category": "Invoice",
        "confidence": 0.94,
        "reasoning": "Contains invoice number and payment amount"
    })
    
    result = llm_classifier._parse_response(response, email)
    
    assert result is not None
    assert result.category == EmailCategory.INVOICE
    assert result.confidence == 0.94
    assert "LLM:" in result.reasoning


def test_parse_json_with_text_wrapper(llm_classifier):
    """Парсить JSON обрамленный текстом"""
    
    email = EmailDocument(
        message_id="test-parse-2",
        from_email="test@example.com",
        to_email="receiver@company.com",
        subject="Test",
        body_text="Test",
        size_bytes=100,
        received_at=datetime.utcnow()
    )
    
    response = """
    Based on the email content, here's my classification:
    
    {
      "category": "Support",
      "confidence": 0.89,
      "reasoning": "Customer issue with urgency"
    }
    
    This is clearly a support ticket.
    """
    
    result = llm_classifier._parse_response(response, email)
    
    assert result is not None
    assert result.category == EmailCategory.SUPPORT
    assert result.confidence == 0.89


def test_parse_invalid_json(llm_classifier):
    """Обработать невалидный JSON"""
    
    email = EmailDocument(
        message_id="test-parse-3",
        from_email="test@example.com",
        to_email="receiver@company.com",
        subject="Test",
        body_text="Test",
        size_bytes=100,
        received_at=datetime.utcnow()
    )
    
    response = "This is not JSON at all, just plain text"
    
    result = llm_classifier._parse_response(response, email)
    
    assert result is None


def test_parse_json_with_unknown_category(llm_classifier):
    """Обработать неизвестную категорию → map to OTHER"""
    
    email = EmailDocument(
        message_id="test-parse-4",
        from_email="test@example.com",
        to_email="receiver@company.com",
        subject="Test",
        body_text="Test",
        size_bytes=100,
        received_at=datetime.utcnow()
    )
    
    response = json.dumps({
        "category": "UnknownCategory",
        "confidence": 0.85,
        "reasoning": "Some reason"
    })
    
    result = llm_classifier._parse_response(response, email)
    
    assert result is not None
    assert result.category == EmailCategory.OTHER


def test_parse_json_confidence_clamping(llm_classifier):
    """Проверить что confidence clamp to 0.1-0.99"""
    
    email = EmailDocument(
        message_id="test-parse-5",
        from_email="test@example.com",
        to_email="receiver@company.com",
        subject="Test",
        body_text="Test",
        size_bytes=100,
        received_at=datetime.utcnow()
    )
    
    # Test upper bound
    response_high = json.dumps({
        "category": "Invoice",
        "confidence": 1.5,  # Invalid: > 1.0
        "reasoning": "Test"
    })
    
    result_high = llm_classifier._parse_response(response_high, email)
    assert result_high.confidence == 0.99
    
    # Test lower bound
    response_low = json.dumps({
        "category": "Invoice",
        "confidence": 0.05,  # Invalid: < 0.1
        "reasoning": "Test"
    })
    
    result_low = llm_classifier._parse_response(response_low, email)
    assert result_low.confidence == 0.1


# ==============================================================================
# TEST: Error Handling
# ==============================================================================

@pytest.mark.asyncio
async def test_classify_ollama_timeout(llm_classifier, ollama_client, embedding_service):
    """Обработать timeout от Ollama"""
    
    email = EmailDocument(
        message_id="test-timeout",
        from_email="test@example.com",
        to_email="support@company.com",
        subject="Test email",
        body_text="Test content",
        size_bytes=500,
        received_at=datetime.utcnow()
    )
    
    embedding_service.find_similar_emails = AsyncMock(return_value=[])
    ollama_client.complete = AsyncMock(return_value=None)
    
    result = await llm_classifier.classify(email, use_few_shot=False)
    
    assert result is None
    assert llm_classifier.stats['failed'] == 1


@pytest.mark.asyncio
async def test_classify_empty_response(llm_classifier, ollama_client, embedding_service):
    """Обработать пустой ответ от LLM"""
    
    email = EmailDocument(
        message_id="test-empty",
        from_email="test@example.com",
        to_email="support@company.com",
        subject="Test",
        body_text="Test",
        size_bytes=500,
        received_at=datetime.utcnow()
    )
    
    embedding_service.find_similar_emails = AsyncMock(return_value=[])
    ollama_client.complete = AsyncMock(return_value="")
    
    result = await llm_classifier.classify(email, use_few_shot=False)
    
    assert result is None


# ==============================================================================
# TEST: Statistics
# ==============================================================================

@pytest.mark.asyncio
async def test_classifier_stats(llm_classifier, ollama_client, embedding_service):
    """Проверить сбор статистики"""
    
    embedding_service.find_similar_emails = AsyncMock(return_value=[])
    
    # Классифицировать несколько писем
    for i in range(5):
        email = EmailDocument(
            message_id=f"test-stats-{i}",
            from_email=f"sender{i}@example.com",
            to_email="receiver@company.com",
            subject=f"Test {i}",
            body_text="Test content",
            size_bytes=500,
            received_at=datetime.utcnow()
        )
        
        mock_response = json.dumps({
            "category": "Invoice",
            "confidence": 0.90 + (i * 0.01),
            "reasoning": "Test classification"
        })
        
        ollama_client.complete = AsyncMock(return_value=mock_response)
        await llm_classifier.classify(email, use_few_shot=False)
    
    stats = llm_classifier.get_stats()
    
    assert stats['total'] == 5
    assert stats['successful'] == 5
    assert stats['failed'] == 0
    assert stats['success_rate'] == 100.0
    assert stats['avg_confidence'] > 0.85
    assert 'avg_processing_time_ms' in stats


@pytest.mark.asyncio
async def test_reset_stats(llm_classifier, ollama_client, embedding_service):
    """Проверить сброс статистики"""
    
    email = EmailDocument(
        message_id="test-reset",
        from_email="test@example.com",
        to_email="receiver@company.com",
        subject="Test",
        body_text="Test",
        size_bytes=100,
        received_at=datetime.utcnow()
    )
    
    embedding_service.find_similar_emails = AsyncMock(return_value=[])
    
    mock_response = json.dumps({
        "category": "Invoice",
        "confidence": 0.95,
        "reasoning": "Test"
    })
    
    ollama_client.complete = AsyncMock(return_value=mock_response)
    await llm_classifier.classify(email, use_few_shot=False)
    
    stats_before = llm_classifier.get_stats()
    assert stats_before['total'] == 1
    
    # Сбросить
    llm_classifier.reset_stats()
    
    stats_after = llm_classifier.get_stats()
    assert stats_after['total'] == 0
    assert stats_after['successful'] == 0


# ==============================================================================
# TEST: Few-Shot Learning
# ==============================================================================

@pytest.mark.asyncio
async def test_few_shot_improves_accuracy(llm_classifier, ollama_client, embedding_service):
    """Проверить что few-shot повышает точность"""
    
    email = EmailDocument(
        message_id="test-few-shot",
        from_email="ambiguous@example.com",
        to_email="receiver@company.com",
        subject="Request",
        body_text="Can you help with this?",
        size_bytes=400,
        received_at=datetime.utcnow()
    )
    
    # Without few-shot
    embedding_service.find_similar_emails = AsyncMock(return_value=[])
    
    mock_response_no_fs = json.dumps({
        "category": "Other",
        "confidence": 0.55,
        "reasoning": "Ambiguous request"
    })
    
    ollama_client.complete = AsyncMock(return_value=mock_response_no_fs)
    result_no_fs = await llm_classifier.classify(email, use_few_shot=False)
    
    # With few-shot
    embedding_service.find_similar_emails = AsyncMock(return_value=[
        {
            'id': 1,
            'category': 'Support',
            'confidence': 0.92,
            'subject': 'Help needed',
            'from_email': 'customer@example.com',
            'body_text': 'Can you assist?',
            'similarity': 0.88
        }
    ])
    
    mock_response_with_fs = json.dumps({
        "category": "Support",
        "confidence": 0.87,
        "reasoning": "Similar to past support requests"
    })
    
    ollama_client.complete = AsyncMock(return_value=mock_response_with_fs)
    result_with_fs = await llm_classifier.classify(email, use_few_shot=True)
    
    # Few-shot should increase confidence
    assert result_with_fs.confidence > result_no_fs.confidence
