"""
Response Generator Service - Automated email response generation.

Hybrid approach:
- Template-based (fast, <100ms) for high-confidence classifications
- LLM-based (smart, 2-3s) for low-confidence or complex cases

Features:
- Language detection (RU/EN)
- Tone detection (formal, professional, friendly, urgent)
- Signature extraction and preservation
- Personalization with variables
"""

import logging
import re
import time
from typing import Optional, Tuple, Dict, Any
from datetime import datetime

from app.models.email_models import EmailDocument, EmailCategory, Classification
from app.services.response_templates import (
    ResponseTemplateService, ResponseTemplate, ResponseLanguage, ResponseTone
)
from app.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class SignatureExtractor:
    """Извлечение подписи из письма"""
    
    SIGNATURE_PATTERNS = [
        r'(?:--\s*\n|^-{2,}\s*$)(.*?)$',  # -- signature
        r'(?:С\s+уважением|Best regards|Regards|Спасибо),?\s*\n(.*?)$',
        r'(?:^|\n)--\s*\n([\s\S]*)',  # Email standard
    ]
    
    @staticmethod
    def extract(body: str) -> Optional[str]:
        """Извлечь подпись из тела письма"""
        
        if not body or len(body) < 20:
            return None
        
        lines = body.split('\n')
        
        # Подпись обычно в конце (последние 5-10 строк)
        potential_signature = '\n'.join(lines[-10:])
        
        for pattern in SignatureExtractor.SIGNATURE_PATTERNS:
            match = re.search(pattern, potential_signature, re.MULTILINE | re.IGNORECASE)
            if match:
                signature = match.group(1).strip() if match.lastindex else match.group(0).strip()
                
                # Проверить что это выглядит как подпись
                if 3 <= len(signature.split('\n')) <= 8 and len(signature) < 500:
                    return signature
        
        return None


class LanguageDetector:
    """Определение языка письма"""
    
    RUSSIAN_CHARS = 'абвгдежзийклмнопрстуфхцчшщъыьэюяАБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ'
    
    @staticmethod
    def detect(text: str) -> ResponseLanguage:
        """
        Определить язык текста
        
        Args:
            text: Текст для определения
            
        Returns:
            ResponseLanguage.RUSSIAN или ResponseLanguage.ENGLISH
        """
        
        if not text:
            return ResponseLanguage.ENGLISH
        
        russian_count = sum(1 for c in text if c in LanguageDetector.RUSSIAN_CHARS)
        total_chars = len([c for c in text if c.isalpha()])
        
        if total_chars == 0:
            return ResponseLanguage.ENGLISH
        
        russian_ratio = russian_count / total_chars
        
        # Если больше 30% русских букв - русский язык
        return ResponseLanguage.RUSSIAN if russian_ratio > 0.3 else ResponseLanguage.ENGLISH


class ToneDetector:
    """Определение тональности письма"""
    
    TONE_KEYWORDS = {
        ResponseTone.URGENT: [
            'urgent', 'asap', 'срочно', 'экстренно', 'критично',
            'immediately', 'неотложно'
        ],
        ResponseTone.FORMAL: [
            'hereby', 'formal', 'официально', 'формальный',
            'уведомляем', 'доводим', 'ставим в известность'
        ],
        ResponseTone.FRIENDLY: [
            'thanks', 'appreciate', 'спасибо', 'огромное спасибо',
            'thank you very much', 'благодарны'
        ]
    }
    
    @staticmethod
    def detect(subject: str, body: str) -> ResponseTone:
        """
        Определить тональность письма
        
        Args:
            subject: Subject письма
            body: Body письма
            
        Returns:
            ResponseTone
        """
        
        text = f"{subject} {body}".lower()
        
        tone_scores = {tone: 0 for tone in ResponseTone}
        
        for tone, keywords in ToneDetector.TONE_KEYWORDS.items():
            for keyword in keywords:
                tone_scores[tone] += text.count(keyword)
        
        # Вернуть tone с наибольшим счетом, или professional по умолчанию
        best_tone = max(tone_scores, key=tone_scores.get)
        
        if tone_scores[best_tone] == 0:
            return ResponseTone.PROFESSIONAL
        
        return best_tone


class ResponseGenerator:
    """
    Генератор автоматических ответов
    Hybrid подход: Template (70%) + LLM (30%)
    """
    
    def __init__(
        self,
        template_service: ResponseTemplateService,
        ollama_client: Optional[OllamaClient] = None
    ):
        self.templates = template_service
        self.ollama = ollama_client
        
        self.stats = {
            'total_generated': 0,
            'from_template': 0,
            'from_llm': 0,
            'approval_required': 0,
            'avg_latency_ms': 0
        }
    
    async def generate(
        self,
        email: EmailDocument,
        classification: Classification
    ) -> ResponseTemplate:
        """
        Сгенерировать ответ на письмо
        
        Args:
            email: Входящее письмо
            classification: Классификация письма
            
        Returns:
            ResponseTemplate с ответом
        """
        
        start_time = time.time()
        
        try:
            # Определить язык и тональность
            language = LanguageDetector.detect(email.body_text or "")
            tone = ToneDetector.detect(email.subject or "", email.body_text or "")
            
            # Получить категорию из классификации
            category = classification.category.value
            
            # Попробовать template first (если confidence высокая)
            if classification.confidence > 0.85:
                response = await self._generate_from_template(
                    email, category, language, tone
                )
                
                if response:
                    response.generated_from = "template"
                    self.stats['from_template'] += 1
                    self._update_stats(time.time() - start_time)
                    return response
            
            # Fallback на LLM если template не подходит
            if self.ollama:
                response = await self._generate_from_llm(
                    email, category, language, tone, classification
                )
                
                if response:
                    response.generated_from = "llm"
                    self.stats['from_llm'] += 1
                    self._update_stats(time.time() - start_time)
                    return response
            
            # Final fallback: базовый template ответ
            response = self._generate_fallback(email, language, tone)
            response.generated_from = "template"
            self.stats['from_template'] += 1
            self._update_stats(time.time() - start_time)
            return response
        
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            # Вернуть fallback
            return self._generate_fallback(email, ResponseLanguage.ENGLISH, ResponseTone.PROFESSIONAL)
    
    async def _generate_from_template(
        self,
        email: EmailDocument,
        category: str,
        language: ResponseLanguage,
        tone: ResponseTone
    ) -> Optional[ResponseTemplate]:
        """Сгенерировать ответ из шаблона"""
        
        # Получить шаблон
        template = self.templates.get_template(category, language, tone)
        
        if not template:
            return None
        
        try:
            # Извлечь переменные из письма
            variables = self._extract_variables(email)
            
            # Рендерить шаблон
            subject, body = self.templates.render(template, variables)
            
            # Добавить signature из исходного письма
            signature = SignatureExtractor.extract(email.body_text or "")
            if signature:
                body += f"\n\n{signature}"
            
            return ResponseTemplate(
                email_id=email.id if hasattr(email, 'id') else 0,
                subject=subject,
                body=body,
                language=language,
                tone=tone,
                template_id=template.id,
                variables_used=variables,
                confidence=0.95,  # Template responses имеют высокую confidence
                requires_approval=False  # Template responses не требуют одобрения
            )
        
        except Exception as e:
            logger.error(f"Error rendering template: {e}")
            return None
    
    async def _generate_from_llm(
        self,
        email: EmailDocument,
        category: str,
        language: ResponseLanguage,
        tone: ResponseTone,
        classification: Classification
    ) -> Optional[ResponseTemplate]:
        """Сгенерировать ответ через LLM"""
        
        if not self.ollama:
            return None
        
        try:
            # Построить prompt
            system_prompt = self._build_system_prompt(language, tone, category)
            user_prompt = self._build_user_prompt(email, classification, language)
            
            # Вызвать LLM
            response = await self.ollama.complete(
                prompt=user_prompt,
                system=system_prompt,
                temperature=0.5,  # Moderate creativity
                max_tokens=500
            )
            
            if not response:
                return None
            
            # Парсить response (format: SUBJECT\n\nBODY)
            parts = response.split('\n\n', 1)
            subject = parts[0].replace('Subject: ', '').strip()
            body = parts[1] if len(parts) > 1 else parts[0]
            
            # Добавить signature
            signature = SignatureExtractor.extract(email.body_text or "")
            if signature:
                body += f"\n\n{signature}"
            
            return ResponseTemplate(
                email_id=email.id if hasattr(email, 'id') else 0,
                subject=subject,
                body=body,
                language=language,
                tone=tone,
                template_id=None,
                confidence=classification.confidence,
                requires_approval=True  # LLM responses требуют одобрения
            )
        
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return None
    
    def _generate_fallback(
        self,
        email: EmailDocument,
        language: ResponseLanguage,
        tone: ResponseTone
    ) -> ResponseTemplate:
        """Базовый fallback ответ"""
        
        if language == ResponseLanguage.RUSSIAN:
            subject = "Re: " + (email.subject or "Ваше письмо")
            body = f"""Добрый день!

Спасибо за ваше письмо. Мы рассмотрели вашу заявку и свяжемся с вами в ближайшее время.

С уважением."""
        else:
            subject = "Re: " + (email.subject or "Your message")
            body = f"""Hello,

Thank you for your email. We have received your message and will get back to you shortly.

Best regards."""
        
        return ResponseTemplate(
            email_id=email.id if hasattr(email, 'id') else 0,
            subject=subject,
            body=body,
            language=language,
            tone=tone,
            generated_from="fallback",
            template_id=None,
            confidence=0.5,
            requires_approval=True
        )
    
    def _extract_variables(self, email: EmailDocument) -> Dict[str, str]:
        """Извлечь переменные из письма для подстановки"""
        
        # Извлечь имя отправителя
        from_name = "User"
        if email.from_email:
            # Попробовать извлечь имя из email
            match = re.search(r'([A-Za-zА-Яа-я]+)', email.from_email.split('@')[0])
            if match:
                from_name = match.group(1).capitalize()
        
        variables = {
            'name': from_name,
            'our_company': 'Company Name',
            'support_team': 'Support Team',
            'invoice_number': 'N/A',
            'order_number': 'N/A',
            'ticket_number': 'N/A',
            'amount': 'N/A',
            'currency': 'RUB',
            'delivery_date': 'TBD'
        }
        
        # Попытаться найти дополнительные переменные в тексте
        # (в реальном коде использовать Named Entity Recognition)
        
        return variables
    
    def _build_system_prompt(
        self,
        language: ResponseLanguage,
        tone: ResponseTone,
        category: str
    ) -> str:
        """Построить system prompt для LLM"""
        
        if language == ResponseLanguage.RUSSIAN:
            return f"""Вы помощник по генерации профессиональных ответов на деловые письма на русском языке.

Стиль: {tone.value.upper()}
Категория письма: {category}

Требования:
1. Ответ должен быть вежливым и профессиональным
2. Используйте нейтральный или дружелюбный тон
3. Начните с приветствия
4. Ясно и кратко выразите основную идею
5. Завершите вежливым прощанием

Формат ответа:
[Тема ответа]

[Тело письма]"""
        else:
            return f"""You are an assistant for generating professional responses to business emails in English.

Style: {tone.value.upper()}
Email Category: {category}

Requirements:
1. Response should be polite and professional
2. Use neutral or friendly tone
3. Start with a greeting
4. Express the main idea clearly and concisely
5. End with a polite closing

Response format:
[Subject line]

[Email body]"""
    
    def _build_user_prompt(
        self,
        email: EmailDocument,
        classification: Classification,
        language: ResponseLanguage
    ) -> str:
        """Построить user prompt для LLM"""
        
        if language == ResponseLanguage.RUSSIAN:
            return f"""Напишите ответ на следующее письмо:

От: {email.from_email}
Тема: {email.subject}

Текст письма:
{email.body_text[:500] if email.body_text else ''}

Классификация: {classification.category}
Confidence: {classification.confidence:.2f}

Пожалуйста, напишите профессиональный ответ на это письмо."""
        else:
            return f"""Write a response to the following email:

From: {email.from_email}
Subject: {email.subject}

Email body:
{email.body_text[:500] if email.body_text else ''}

Classification: {classification.category}
Confidence: {classification.confidence:.2f}

Please write a professional response to this email."""
    
    def _update_stats(self, elapsed_seconds: float):
        """Обновить статистику"""
        self.stats['total_generated'] += 1
        
        elapsed_ms = elapsed_seconds * 1000
        old_avg = self.stats['avg_latency_ms']
        count = self.stats['total_generated']
        
        self.stats['avg_latency_ms'] = (
            (old_avg * (count - 1) + elapsed_ms) / count
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику"""
        return {
            'total_generated': self.stats['total_generated'],
            'from_template': self.stats['from_template'],
            'from_llm': self.stats['from_llm'],
            'approval_required': self.stats['approval_required'],
            'avg_latency_ms': round(self.stats['avg_latency_ms'], 2)
        }
