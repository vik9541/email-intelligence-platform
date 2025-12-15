"""
Response Template Service - Template-based email response generation.

Provides pre-built templates for common email categories:
- Invoices (RU/EN)
- Purchase Orders (RU/EN)
- Support tickets (RU/EN)

Fast response generation (<50ms) with variable substitution.
"""

import json
import logging
from typing import Optional, Dict, List, Any
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ResponseTone(str, Enum):
    """Тональность ответа"""
    FORMAL = "formal"          # Официальный
    PROFESSIONAL = "professional"  # Профессиональный
    FRIENDLY = "friendly"      # Дружелюбный
    URGENT = "urgent"          # Срочный


class ResponseLanguage(str, Enum):
    """Язык ответа"""
    RUSSIAN = "ru"
    ENGLISH = "en"


class EmailTemplate(BaseModel):
    """Email шаблон"""
    id: str
    category: str  # invoice, order, support, etc
    language: ResponseLanguage
    tone: ResponseTone
    
    subject_template: str
    body_template: str
    
    variables: List[str] = []  # {name}, {company}, {amount}, etc
    
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ResponseTemplate(BaseModel):
    """Сгенерированный ответ"""
    id: str = Field(default_factory=lambda: str(datetime.utcnow().timestamp()))
    email_id: int
    
    subject: str
    body: str
    
    language: ResponseLanguage
    tone: ResponseTone
    
    generated_from: str  # "template" или "llm"
    template_id: Optional[str] = None
    
    variables_used: Dict[str, str] = {}
    
    confidence: float = Field(ge=0.0, le=1.0)
    requires_approval: bool = True
    
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ResponseTemplateService:
    """
    Сервис управления шаблонами ответов
    Хранит предустановки для быстрой генерации
    """
    
    # Встроенные шаблоны (в продакшене хранить в БД)
    DEFAULT_TEMPLATES = {
        # ========================================
        # INVOICE TEMPLATES
        # ========================================
        "invoice_ru_professional": EmailTemplate(
            id="invoice_ru_prof",
            category="invoice",
            language=ResponseLanguage.RUSSIAN,
            tone=ResponseTone.PROFESSIONAL,
            subject_template="Спасибо за счет №{invoice_number}",
            body_template="""Добрый день, {name}!

Спасибо за высылку счета №{invoice_number} на сумму {amount} {currency}.

Документ получен и обработан. Оплата будет произведена согласно условиям платежа.

С уважением,
{our_company}""",
            variables=["name", "invoice_number", "amount", "currency", "our_company"]
        ),
        
        "invoice_en_professional": EmailTemplate(
            id="invoice_en_prof",
            category="invoice",
            language=ResponseLanguage.ENGLISH,
            tone=ResponseTone.PROFESSIONAL,
            subject_template="Thank you for Invoice #{invoice_number}",
            body_template="""Hello {name},

Thank you for sending invoice #{invoice_number} for the amount of {amount} {currency}.

We have received and processed the document. Payment will be made according to the payment terms.

Best regards,
{our_company}""",
            variables=["name", "invoice_number", "amount", "currency", "our_company"]
        ),
        
        "invoice_ru_formal": EmailTemplate(
            id="invoice_ru_formal",
            category="invoice",
            language=ResponseLanguage.RUSSIAN,
            tone=ResponseTone.FORMAL,
            subject_template="Подтверждение получения счета №{invoice_number}",
            body_template="""Уважаемый(-ая) {name},

Настоящим подтверждаем получение счета №{invoice_number} на сумму {amount} {currency}.

Документ принят к обработке. Оплата будет осуществлена в соответствии с условиями договора.

С уважением,
{our_company}""",
            variables=["name", "invoice_number", "amount", "currency", "our_company"]
        ),
        
        # ========================================
        # PURCHASE ORDER TEMPLATES
        # ========================================
        "purchase_order_ru_professional": EmailTemplate(
            id="order_ru_prof",
            category="purchase_order",
            language=ResponseLanguage.RUSSIAN,
            tone=ResponseTone.PROFESSIONAL,
            subject_template="Подтверждение заказа №{order_number}",
            body_template="""Добрый день, {name}!

Спасибо за ваш заказ №{order_number}.

Заказ принят и находится в обработке. Статус выполнения будет доступен в нашей системе.
Предполагаемая дата доставки: {delivery_date}

С уважением,
{our_company}""",
            variables=["name", "order_number", "delivery_date", "our_company"]
        ),
        
        "purchase_order_en_professional": EmailTemplate(
            id="order_en_prof",
            category="purchase_order",
            language=ResponseLanguage.ENGLISH,
            tone=ResponseTone.PROFESSIONAL,
            subject_template="Order Confirmation #{order_number}",
            body_template="""Hello {name},

Thank you for your order #{order_number}.

Your order has been received and is being processed. You can track the status in our system.
Expected delivery date: {delivery_date}

Best regards,
{our_company}""",
            variables=["name", "order_number", "delivery_date", "our_company"]
        ),
        
        "purchase_order_ru_friendly": EmailTemplate(
            id="order_ru_friendly",
            category="purchase_order",
            language=ResponseLanguage.RUSSIAN,
            tone=ResponseTone.FRIENDLY,
            subject_template="Ваш заказ №{order_number} принят!",
            body_template="""Привет, {name}!

Отличные новости - ваш заказ №{order_number} уже в работе!

Мы позаботимся о том, чтобы все было выполнено качественно и в срок.
Ожидаемая доставка: {delivery_date}

С наилучшими пожеланиями,
Команда {our_company}""",
            variables=["name", "order_number", "delivery_date", "our_company"]
        ),
        
        # ========================================
        # SUPPORT TEMPLATES
        # ========================================
        "support_ru_urgent": EmailTemplate(
            id="support_ru_urgent",
            category="support",
            language=ResponseLanguage.RUSSIAN,
            tone=ResponseTone.URGENT,
            subject_template="Ваша заявка #{ticket_number} - Принята в работу",
            body_template="""Добрый день, {name}!

Спасибо за обращение. Ваша заявка #{ticket_number} была зарегистрирована и направлена в соответствующий отдел.

ПРИОРИТЕТ: ВЫСОКИЙ
Время ответа: 2 часа

Мы свяжемся с вами в кратчайшие сроки.

С уважением,
{support_team}""",
            variables=["name", "ticket_number", "support_team"]
        ),
        
        "support_en_urgent": EmailTemplate(
            id="support_en_urgent",
            category="support",
            language=ResponseLanguage.ENGLISH,
            tone=ResponseTone.URGENT,
            subject_template="Your Request #{ticket_number} - Received",
            body_template="""Hello {name},

Thank you for contacting us. Your request #{ticket_number} has been received and assigned to our support team.

PRIORITY: HIGH
Response time: 2 hours

We will get back to you shortly.

Best regards,
{support_team}""",
            variables=["name", "ticket_number", "support_team"]
        ),
        
        "support_ru_professional": EmailTemplate(
            id="support_ru_prof",
            category="support",
            language=ResponseLanguage.RUSSIAN,
            tone=ResponseTone.PROFESSIONAL,
            subject_template="Заявка #{ticket_number} - Получено",
            body_template="""Добрый день, {name}!

Ваша заявка #{ticket_number} получена и зарегистрирована в нашей системе.

Наши специалисты рассмотрят ваш запрос и свяжутся с вами в течение рабочего дня.

С уважением,
{support_team}""",
            variables=["name", "ticket_number", "support_team"]
        ),
        
        "support_en_professional": EmailTemplate(
            id="support_en_prof",
            category="support",
            language=ResponseLanguage.ENGLISH,
            tone=ResponseTone.PROFESSIONAL,
            subject_template="Ticket #{ticket_number} - Received",
            body_template="""Hello {name},

Your ticket #{ticket_number} has been received and registered in our system.

Our specialists will review your request and contact you within one business day.

Best regards,
{support_team}""",
            variables=["name", "ticket_number", "support_team"]
        ),
    }
    
    def __init__(self):
        self.templates: Dict[str, EmailTemplate] = self.DEFAULT_TEMPLATES.copy()
    
    def get_template(
        self,
        category: str,
        language: ResponseLanguage,
        tone: ResponseTone
    ) -> Optional[EmailTemplate]:
        """
        Получить шаблон по параметрам
        
        Args:
            category: invoice, purchase_order, support, etc
            language: ru или en
            tone: formal, professional, friendly, urgent
            
        Returns:
            EmailTemplate или None если не найден
        """
        
        # Попробовать точное совпадение
        template_id = f"{category}_{language.value}_{tone.value}"
        
        for tid, template in self.templates.items():
            if template.category == category and \
               template.language == language and \
               template.tone == tone and \
               template.is_active:
                return template
        
        # Fallback на professional tone
        if tone != ResponseTone.PROFESSIONAL:
            return self.get_template(category, language, ResponseTone.PROFESSIONAL)
        
        # Fallback на English если Russian не найден
        if language == ResponseLanguage.RUSSIAN:
            return self.get_template(category, ResponseLanguage.ENGLISH, tone)
        
        logger.warning(
            f"No template found for {category}/{language.value}/{tone.value}"
        )
        return None
    
    def list_templates(
        self,
        category: Optional[str] = None,
        language: Optional[ResponseLanguage] = None
    ) -> List[EmailTemplate]:
        """Получить список доступных шаблонов"""
        
        results = []
        
        for template in self.templates.values():
            if not template.is_active:
                continue
            
            if category and template.category != category:
                continue
            
            if language and template.language != language:
                continue
            
            results.append(template)
        
        return results
    
    def render(
        self,
        template: EmailTemplate,
        variables: Dict[str, str]
    ) -> tuple[str, str]:
        """
        Рендерить шаблон с переменными
        
        Args:
            template: EmailTemplate
            variables: Dict[name, value]
            
        Returns:
            (subject, body)
        """
        
        try:
            # Проверить обязательные переменные
            missing_vars = set(template.variables) - set(variables.keys())
            
            if missing_vars:
                logger.warning(f"Missing template variables: {missing_vars}")
                # Fill missing with placeholders
                for var in missing_vars:
                    variables[var] = f"[{var}]"
            
            # Рендерить
            subject = template.subject_template.format(**variables)
            body = template.body_template.format(**variables)
            
            return subject, body
        
        except KeyError as e:
            logger.error(f"Missing variable in template: {e}")
            raise ValueError(f"Missing required variable: {e}")
    
    def add_template(self, template: EmailTemplate):
        """Добавить новый шаблон"""
        self.templates[template.id] = template
        logger.info(f"Added template: {template.id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику шаблонов"""
        
        active_count = sum(1 for t in self.templates.values() if t.is_active)
        
        by_category = {}
        for template in self.templates.values():
            if template.is_active:
                cat = template.category
                by_category[cat] = by_category.get(cat, 0) + 1
        
        by_language = {}
        for template in self.templates.values():
            if template.is_active:
                lang = template.language.value
                by_language[lang] = by_language.get(lang, 0) + 1
        
        return {
            'total_templates': len(self.templates),
            'active_templates': active_count,
            'by_category': by_category,
            'by_language': by_language
        }
