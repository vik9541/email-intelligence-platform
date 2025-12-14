"""
Tests for Email Classifier Service

Tests Stage 1 (Rules) and Stage 2 (LLM) classification.
"""

import pytest

from app.services.email_classifier import (
    Classification,
    EmailCategory,
    EmailClassifierService,
)


class TestRulesClassification:
    """Test Stage 1: Rules-based classification."""

    @pytest.mark.asyncio
    async def test_classify_invoice_email(self):
        """Test invoice classification with high confidence."""
        classifier = EmailClassifierService()

        email_text = """
        Dear Customer,
        
        Please find attached invoice INV-123456 for your recent purchase.
        Total amount: $1,234.56
        Payment due: 2025-12-31
        
        Best regards,
        Accounting Team
        """
        subject = "Invoice INV-123456 - Payment Due"

        result = await classifier.classify(email_text, subject)

        assert result.category == EmailCategory.INVOICE
        assert result.confidence >= 0.85
        assert result.method == "rules"
        assert result.requires_erp_action is True
        assert result.erp_action_type == "update_invoice"

    @pytest.mark.asyncio
    async def test_classify_purchase_order(self):
        """Test PO classification."""
        classifier = EmailClassifierService()

        email_text = """
        Purchase Order Confirmation
        
        PO-98765
        
        Items:
        1. Widget A x 100
        2. Widget B x 50
        
        Please ship by 2025-12-20.
        """
        subject = "PO-98765 Confirmation"

        result = await classifier.classify(email_text, subject)

        assert result.category == EmailCategory.PURCHASE_ORDER
        assert result.confidence >= 0.85
        assert result.method == "rules"
        assert result.requires_erp_action is True
        assert result.erp_action_type == "create_order"

    @pytest.mark.asyncio
    async def test_classify_support_request(self):
        """Test support request classification."""
        classifier = EmailClassifierService()

        email_text = """
        Hi Support Team,
        
        I'm having an issue with my order. The tracking number doesn't work
        and I need help resolving this problem.
        
        Ticket #12345
        """
        subject = "Help - Order Issue"

        result = await classifier.classify(email_text, subject)

        assert result.category == EmailCategory.SUPPORT_REQUEST
        assert result.confidence >= 0.8
        assert result.requires_erp_action is False

    @pytest.mark.asyncio
    async def test_classify_sales_inquiry(self):
        """Test sales inquiry classification."""
        classifier = EmailClassifierService()

        email_text = """
        Hello,
        
        I'm interested in purchasing your product. Could you please send me
        a quote for 500 units? Also, what's your pricing for bulk orders?
        
        Thanks!
        """
        subject = "Quote Request"

        result = await classifier.classify(email_text, subject)

        assert result.category == EmailCategory.SALES_INQUIRY
        assert result.confidence >= 0.8

    @pytest.mark.asyncio
    async def test_classify_unknown_email(self):
        """Test unknown/unclassifiable email."""
        classifier = EmailClassifierService()

        email_text = """
        This is a random email with no clear category.
        Just some text here.
        """
        subject = "Random Email"

        result = await classifier.classify(email_text, subject)

        # Should have low confidence
        assert result.confidence < 0.7


class TestEntityExtraction:
    """Test entity extraction from classified emails."""

    def test_extract_invoice_entities(self):
        """Test extracting invoice number and amount."""
        classifier = EmailClassifierService()

        text = "Invoice INV-123456 for $1,234.56 due on 2025-12-31"

        entities = classifier._extract_entities(text, EmailCategory.INVOICE)

        assert "invoice_number" in entities
        assert entities["invoice_number"] == "INV-123456"
        assert "amount" in entities

    def test_extract_po_entities(self):
        """Test extracting PO number."""
        classifier = EmailClassifierService()

        text = "Purchase Order PO-98765 has been approved"

        entities = classifier._extract_entities(text, EmailCategory.PURCHASE_ORDER)

        assert "po_number" in entities
        assert entities["po_number"] == "PO-98765"


class TestClassificationModel:
    """Test Classification Pydantic model."""

    def test_classification_creation(self):
        """Test creating Classification object."""
        classification = Classification(
            category=EmailCategory.INVOICE,
            confidence=0.95,
            method="rules",
            entities={"invoice_number": "INV-123456"},
            requires_erp_action=True,
            erp_action_type="update_invoice",
        )

        assert classification.category == EmailCategory.INVOICE
        assert classification.confidence == 0.95
        assert classification.method == "rules"
        assert classification.requires_erp_action is True

    def test_confidence_validation(self):
        """Test confidence must be between 0 and 1."""
        with pytest.raises(ValueError):
            Classification(
                category=EmailCategory.INVOICE,
                confidence=1.5,  # Invalid: > 1
                method="rules",
            )


class TestLLMClassification:
    """Test Stage 2: LLM-based classification."""

    @pytest.mark.asyncio
    async def test_llm_fallback_for_low_confidence(self):
        """Test LLM is used when rules confidence is low."""
        classifier = EmailClassifierService()

        # Ambiguous email
        email_text = "I need some help with something related to my account"
        subject = "Question"

        result = await classifier.classify(email_text, subject)

        # Should fallback to LLM (stub returns 0.75 confidence)
        assert result.method == "llm"
        assert result.confidence >= 0.7

    def test_llm_prompt_building(self):
        """Test LLM prompt construction."""
        classifier = EmailClassifierService()

        text = "Test email body"
        subject = "Test Subject"
        examples = [
            {"subject": "Ex1", "text": "Example 1", "category": "invoice"},
            {"subject": "Ex2", "text": "Example 2", "category": "purchase_order"},
        ]

        prompt = classifier._build_llm_prompt(text, subject, examples)

        assert "Classify the following email" in prompt
        assert "Examples:" in prompt
        assert "invoice" in prompt
        assert "Test Subject" in prompt


class TestPerformance:
    """Test classification performance metrics."""

    @pytest.mark.asyncio
    async def test_rules_classification_speed(self):
        """Test that rules classification is fast (< 100ms)."""
        import time

        classifier = EmailClassifierService()

        text = "Invoice INV-123456 for $100"
        subject = "Invoice"

        start = time.time()
        result = await classifier.classify(text, subject)
        duration = time.time() - start

        # Should be very fast (< 0.1s = 100ms)
        assert duration < 0.1
        assert result.method == "rules"

    @pytest.mark.asyncio
    async def test_classification_accuracy_on_test_set(self):
        """Test accuracy on predefined test cases."""
        classifier = EmailClassifierService()

        test_cases = [
            ("Invoice INV-12345", EmailCategory.INVOICE),
            ("PO-98765 order", EmailCategory.PURCHASE_ORDER),
            ("help with issue", EmailCategory.SUPPORT_REQUEST),
            ("quote request", EmailCategory.SALES_INQUIRY),
        ]

        correct = 0
        total = len(test_cases)

        for text, expected_category in test_cases:
            result = await classifier.classify(text, "")
            if result.category == expected_category and result.confidence >= 0.8:
                correct += 1

        accuracy = correct / total

        # Should achieve at least 70% accuracy on simple cases
        assert accuracy >= 0.7
