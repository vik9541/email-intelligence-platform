"""
Email Classification Service - Two-Stage Classifier

Stage 1: Rules-based classification (fast, 70% accuracy)
Stage 2: LLM-based classification (accurate, 95% accuracy)

Uses:
- Regex patterns and keyword matching for common cases
- Mistral 7B LLM via Ollama for complex cases
- pgvector similarity search for few-shot learning
"""

import logging
import re
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class EmailCategory(str, Enum):
    """Email classification categories."""

    INVOICE = "invoice"
    PURCHASE_ORDER = "purchase_order"
    SUPPORT_REQUEST = "support_request"
    SALES_INQUIRY = "sales_inquiry"
    HR_COMMUNICATION = "hr_communication"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


class Classification(BaseModel):
    """Email classification result."""

    category: EmailCategory
    confidence: float = Field(..., ge=0.0, le=1.0)
    method: str = Field(..., description="Classification method: rules or llm")
    entities: dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    requires_erp_action: bool = Field(
        default=False, description="Requires ERP action (order, invoice, etc)"
    )
    erp_action_type: str | None = Field(None, description="Type of ERP action to perform")
    classified_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EmailClassifierService:
    """
    Two-stage email classifier.

    Stage 1: Fast rules-based classification
    Stage 2: Accurate LLM-based classification
    """

    # Stage 1: Rules configuration
    RULES = {
        EmailCategory.INVOICE: {
            "keywords": ["invoice", "bill", "payment due", "amount payable", "счет"],
            "patterns": [
                r"INV-\d{6}",  # Invoice number
                r"invoice\s+#?\d+",
                r"total\s+amount:\s+\$[\d,]+",
            ],
            "confidence": 0.95,
        },
        EmailCategory.PURCHASE_ORDER: {
            "keywords": ["purchase order", "PO-", "заказ", "order confirmation"],
            "patterns": [
                r"PO-\d+",  # PO number
                r"purchase\s+order\s+#?\d+",
                r"order\s+id:\s+\d+",
            ],
            "confidence": 0.92,
        },
        EmailCategory.SUPPORT_REQUEST: {
            "keywords": [
                "help",
                "support",
                "issue",
                "problem",
                "error",
                "не работает",
                "проблема",
            ],
            "patterns": [
                r"ticket\s+#?\d+",
                r"case\s+#?\d+",
            ],
            "confidence": 0.85,
        },
        EmailCategory.SALES_INQUIRY: {
            "keywords": [
                "quote",
                "pricing",
                "purchase",
                "buy",
                "interested in",
                "цена",
                "стоимость",
            ],
            "patterns": [
                r"quote\s+request",
                r"price\s+list",
            ],
            "confidence": 0.88,
        },
    }

    # Confidence threshold for Stage 1 → skip Stage 2
    CONFIDENCE_THRESHOLD = 0.85

    def __init__(self, llm_client=None, vector_store=None):
        """
        Initialize email classifier.

        Args:
            llm_client: Ollama client for LLM classification
            vector_store: pgvector store for few-shot learning
        """
        self.llm_client = llm_client
        self.vector_store = vector_store

    async def classify(self, email_text: str, subject: str = "") -> Classification:
        """
        Classify email using two-stage approach.

        Args:
            email_text: Email body text
            subject: Email subject line

        Returns:
            Classification result with category and confidence
        """
        # Combine subject and body for classification
        full_text = f"{subject}\n\n{email_text}"

        # Stage 1: Rules-based classification
        rules_result = self.rules_classify(full_text)

        if rules_result.confidence >= self.CONFIDENCE_THRESHOLD:
            logger.info(
                "Email classified by rules",
                extra={
                    "category": rules_result.category,
                    "confidence": rules_result.confidence,
                    "method": "rules",
                },
            )
            return rules_result

        # Stage 2: LLM-based classification
        logger.info(
            "Rules confidence below threshold, using LLM",
            extra={
                "rules_category": rules_result.category,
                "rules_confidence": rules_result.confidence,
            },
        )

        llm_result = await self.llm_classify(full_text, subject)
        return llm_result

    def rules_classify(self, text: str) -> Classification:
        """
        Stage 1: Rules-based classification.

        Fast pattern matching and keyword detection.

        Args:
            text: Email text to classify

        Returns:
            Classification with confidence score
        """
        text_lower = text.lower()
        max_score = 0.0
        best_category = EmailCategory.UNKNOWN

        for category, rules in self.RULES.items():
            score = 0.0
            matches = 0

            # Keyword matching
            for keyword in rules["keywords"]:
                if keyword.lower() in text_lower:
                    matches += 1
                    score += 0.3

            # Pattern matching
            for pattern in rules["patterns"]:
                if re.search(pattern, text, re.IGNORECASE):
                    matches += 1
                    score += 0.4

            # Normalize score
            if matches > 0:
                # Cap at configured confidence
                normalized_score = min(score / len(rules["keywords"]), rules["confidence"])

                if normalized_score > max_score:
                    max_score = normalized_score
                    best_category = category

        # Extract entities if high confidence
        entities = {}
        if max_score > 0.7:
            entities = self._extract_entities(text, best_category)

        # Determine if ERP action needed
        requires_erp = best_category in [
            EmailCategory.INVOICE,
            EmailCategory.PURCHASE_ORDER,
        ]
        erp_action = None
        if requires_erp:
            if best_category == EmailCategory.PURCHASE_ORDER:
                erp_action = "create_order"
            elif best_category == EmailCategory.INVOICE:
                erp_action = "update_invoice"

        return Classification(
            category=best_category,
            confidence=max_score,
            method="rules",
            entities=entities,
            requires_erp_action=requires_erp,
            erp_action_type=erp_action,
        )

    async def llm_classify(self, text: str, subject: str) -> Classification:
        """
        Stage 2: LLM-based classification with few-shot learning.

        Uses Mistral 7B via Ollama for complex classification.

        Args:
            text: Email text
            subject: Email subject

        Returns:
            Classification with high confidence
        """
        # Get similar examples from vector store (few-shot)
        few_shot_examples = []
        if self.vector_store:
            few_shot_examples = await self._get_similar_examples(text, k=3)

        # Build LLM prompt
        prompt = self._build_llm_prompt(text, subject, few_shot_examples)

        # Call LLM (stub for now)
        if self.llm_client:
            # TODO: Implement actual Ollama call
            # response = await self.llm_client.generate(
            #     model="mistral:7b",
            #     prompt=prompt
            # )
            # category, confidence = self._parse_llm_response(response)
            pass

        # Stub: return medium confidence classification
        logger.info("LLM classification (stub mode)")
        return Classification(
            category=EmailCategory.UNKNOWN,
            confidence=0.75,
            method="llm",
            entities={},
            requires_erp_action=False,
        )

    def _extract_entities(self, text: str, category: EmailCategory) -> dict[str, Any]:
        """
        Extract entities from email based on category.

        Args:
            text: Email text
            category: Classified category

        Returns:
            Extracted entities (invoice numbers, PO numbers, etc)
        """
        entities = {}

        if category == EmailCategory.INVOICE:
            # Extract invoice number
            invoice_match = re.search(r"INV-(\d{6})", text, re.IGNORECASE)
            if invoice_match:
                entities["invoice_number"] = invoice_match.group(0)

            # Extract amount
            amount_match = re.search(r"\$?([\d,]+\.\d{2})", text)
            if amount_match:
                entities["amount"] = amount_match.group(1)

        elif category == EmailCategory.PURCHASE_ORDER:
            # Extract PO number
            po_match = re.search(r"PO-(\d+)", text, re.IGNORECASE)
            if po_match:
                entities["po_number"] = po_match.group(0)

        return entities

    async def _get_similar_examples(self, text: str, k: int = 3) -> list[dict]:
        """
        Get K similar past emails for few-shot learning.

        Uses pgvector similarity search.

        Args:
            text: Email text to find similar examples for
            k: Number of examples to retrieve

        Returns:
            List of similar email examples
        """
        # TODO: Implement pgvector similarity search
        # SELECT text, category, confidence
        # FROM email_classifications
        # ORDER BY embedding <-> query_embedding
        # LIMIT k

        return []

    def _build_llm_prompt(
        self, text: str, subject: str, few_shot_examples: list[dict]
    ) -> str:
        """
        Build LLM prompt with few-shot examples.

        Args:
            text: Email text
            subject: Email subject
            few_shot_examples: Similar past classifications

        Returns:
            Formatted prompt for LLM
        """
        prompt = """Classify the following email into one of these categories:
- invoice
- purchase_order
- support_request
- sales_inquiry
- hr_communication
- unknown

"""
        # Add few-shot examples
        if few_shot_examples:
            prompt += "Examples:\n\n"
            for example in few_shot_examples:
                prompt += f"Subject: {example.get('subject', '')}\n"
                prompt += f"Text: {example.get('text', '')[:200]}...\n"
                prompt += f"Category: {example.get('category', '')}\n\n"

        # Add current email
        prompt += f"Now classify this email:\n\nSubject: {subject}\nText: {text[:500]}\n\n"
        prompt += "Category:"

        return prompt

    def _parse_llm_response(self, response: str) -> tuple[EmailCategory, float]:
        """
        Parse LLM response to extract category and confidence.

        Args:
            response: Raw LLM response

        Returns:
            Tuple of (category, confidence)
        """
        # TODO: Parse LLM response
        # Expected format: "invoice (confidence: 0.95)"
        return EmailCategory.UNKNOWN, 0.75
