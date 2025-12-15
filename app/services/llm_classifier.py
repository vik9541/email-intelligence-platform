"""
LLM-Based Email Classifier
Few-shot learning classifier через Ollama + Mistral 7B
"""

import json
import logging
import time
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.email_models import (
    EmailDocument,
    Classification,
    EmailCategory
)
from app.services.ollama_client import OllamaClient
from app.services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


class LLMClassifier:
    """
    LLM-based classifier используя Ollama + Mistral 7B
    Few-shot learning с примерами из RAG
    Target: 95%+ accuracy, 700-800ms latency
    """
    
    def __init__(
        self,
        ollama_client: OllamaClient,
        embedding_service: EmbeddingService
    ):
        self.ollama = ollama_client
        self.embedding = embedding_service
        self.stats = {
            'total_classified': 0,
            'successful': 0,
            'failed': 0,
            'confidence_scores': [],
            'processing_times': []
        }
    
    async def classify(
        self,
        email: EmailDocument,
        use_few_shot: bool = True
    ) -> Optional[Classification]:
        """
        Классифицировать письмо с использованием LLM
        
        Args:
            email: EmailDocument для классификации
            use_few_shot: Использовать few-shot learning (RAG)
            
        Returns:
            Classification объект или None если ошибка
        """
        
        start_time = time.time()
        
        try:
            # Получить контекст (похожие письма для few-shot)
            similar_emails = []
            if use_few_shot:
                search_text = f"{email.subject} {email.body_text}"
                similar_emails = await self.embedding.find_similar_emails(
                    search_text,
                    k=3,
                    threshold=0.3
                )
                logger.debug(f"📚 Retrieved {len(similar_emails)} similar emails for few-shot")
            
            # Построить prompt
            prompt = self._build_prompt(email, similar_emails)
            system_prompt = self._build_system_prompt()
            
            # Отправить в LLM
            logger.debug("🤖 Sending request to LLM...")
            response = await self.ollama.complete(
                prompt=prompt,
                system=system_prompt,
                temperature=0.2,  # Low for consistency
                max_tokens=300
            )
            
            if not response:
                logger.warning("⚠️ LLM returned empty response")
                self.stats['failed'] += 1
                return None
            
            # Парсить JSON ответ
            classification = self._parse_response(response, email)
            
            if not classification:
                self.stats['failed'] += 1
                return None
            
            # Update stats
            elapsed_ms = (time.time() - start_time) * 1000
            self.stats['total_classified'] += 1
            self.stats['successful'] += 1
            self.stats['confidence_scores'].append(classification.confidence)
            self.stats['processing_times'].append(elapsed_ms)
            
            logger.info(
                f"✅ LLM classified: {email.message_id} → {classification.category.value} "
                f"({classification.confidence:.2f}) in {elapsed_ms:.0f}ms"
            )
            
            return classification
        
        except Exception as e:
            logger.error(f"❌ LLM classification failed: {e}")
            self.stats['failed'] += 1
            return None
    
    def _build_system_prompt(self) -> str:
        """Построить system prompt для LLM"""
        return """You are an expert email classifier for a business ERP system.

Your task is to classify incoming emails into these categories:
- Invoice: Payment requests, bills, invoices, accounting documents
- PO (Purchase Order): Orders, purchase requests, procurement documents
- Support: Help requests, issues, bugs, complaints, refunds
- Sales: Quotes, proposals, offers, deals, promotions
- HR: Human resources, benefits, training, employment matters
- Newsletter: Marketing content, announcements, newsletters
- Other: Everything else that doesn't fit above categories

Respond ONLY with valid JSON in this exact format:
{
  "category": "Invoice|PO|Support|Sales|HR|Newsletter|Other",
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation of why this category"
}

Rules:
1. Be confident (0.8-0.99) only when very sure
2. Use 0.5-0.7 for borderline cases
3. Consider email context, sender domain, content keywords
4. If multiple categories possible, choose most likely one
5. Never use confidence > 0.99 or < 0.1
6. Reasoning should be concise (max 100 chars)"""
    
    def _build_prompt(
        self,
        email: EmailDocument,
        similar_emails: List[Dict[str, Any]]
    ) -> str:
        """Построить user prompt с few-shot контекстом"""
        
        # Few-shot examples section
        few_shot_section = ""
        if similar_emails:
            few_shot_section = "\n\nSIMILAR PAST EMAILS (for context):\n"
            for i, sim_email in enumerate(similar_emails, 1):
                few_shot_section += f"""
Example {i} (similarity: {sim_email.get('similarity', 0.0):.2f}):
FROM: {sim_email['from_email']}
SUBJECT: {sim_email['subject']}
CLASSIFIED AS: {sim_email['category']} (confidence: {sim_email.get('confidence', 0.0):.2f})
---"""
        
        # Truncate body для экономии tokens
        body_truncated = email.body_text[:1000] if email.body_text else ""
        
        prompt = f"""CLASSIFY THIS EMAIL:

FROM: {email.from_email}
TO: {email.to_email}
SUBJECT: {email.subject}

BODY:
{body_truncated}

{few_shot_section}

Classify this email into one of the 7 categories. Return JSON response only."""
        
        return prompt
    
    def _parse_response(
        self,
        response: str,
        email: EmailDocument
    ) -> Optional[Classification]:
        """Парсить JSON ответ от LLM"""
        try:
            # Найти JSON в ответе (может быть обрамлен текстом)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.error("❌ No JSON found in LLM response")
                logger.debug(f"Response: {response[:200]}")
                return None
            
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            
            # Валидировать поля
            category_str = data.get('category', 'Other').lower()
            
            # Map string to enum
            category_map = {
                'invoice': EmailCategory.INVOICE,
                'po': EmailCategory.PURCHASE_ORDER,
                'purchase_order': EmailCategory.PURCHASE_ORDER,
                'purchase order': EmailCategory.PURCHASE_ORDER,
                'support': EmailCategory.SUPPORT,
                'sales': EmailCategory.SALES,
                'hr': EmailCategory.HR,
                'newsletter': EmailCategory.OTHER,
                'other': EmailCategory.OTHER
            }
            
            category = category_map.get(category_str, EmailCategory.OTHER)
            confidence = float(data.get('confidence', 0.5))
            reasoning = data.get('reasoning', 'LLM classification')
            
            # Ensure confidence is in valid range
            confidence = max(0.1, min(0.99, confidence))
            
            # Get priority from category
            priority_map = {
                EmailCategory.INVOICE: 1,
                EmailCategory.PURCHASE_ORDER: 2,
                EmailCategory.SUPPORT: 3,
                EmailCategory.SALES: 4,
                EmailCategory.HR: 5,
                EmailCategory.OTHER: 6
            }
            
            priority = priority_map.get(category, 6)
            
            return Classification(
                category=category,
                confidence=confidence,
                priority=priority,
                reasoning=f"LLM: {reasoning}",
                requires_review=confidence < 0.75
            )
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse JSON response: {e}")
            logger.debug(f"Response was: {response[:300]}")
            return None
        
        except Exception as e:
            logger.error(f"❌ Error parsing LLM response: {e}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику классификации"""
        success_rate = (
            self.stats['successful'] / self.stats['total_classified'] * 100
            if self.stats['total_classified'] > 0
            else 0
        )
        
        avg_confidence = (
            sum(self.stats['confidence_scores']) / len(self.stats['confidence_scores'])
            if self.stats['confidence_scores']
            else 0
        )
        
        avg_processing_time = (
            sum(self.stats['processing_times']) / len(self.stats['processing_times'])
            if self.stats['processing_times']
            else 0
        )
        
        # Performance target: 700-800ms
        performance_ok = avg_processing_time < 1000
        
        return {
            'total': self.stats['total_classified'],
            'successful': self.stats['successful'],
            'failed': self.stats['failed'],
            'success_rate': round(success_rate, 1),
            'avg_confidence': round(avg_confidence, 2),
            'avg_processing_time_ms': round(avg_processing_time, 1),
            'performance_ok': performance_ok,
            'target_latency': '700-800ms',
            'target_accuracy': '95%+'
        }
    
    def reset_stats(self):
        """Сбросить статистику"""
        self.stats = {
            'total_classified': 0,
            'successful': 0,
            'failed': 0,
            'confidence_scores': [],
            'processing_times': []
        }
        logger.info("📊 LLM classifier stats reset")
