"""
Invoice Extractor Service - Extract structured data from invoice emails.

Parses Russian and English invoice text to extract:
- Invoice number, date, amounts
- VAT calculation
- Payment terms
- Vendor/Customer info
"""

import re
import logging
from typing import Optional, Dict, Any, List
from decimal import Decimal
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CurrencyType(str, Enum):
    """Поддерживаемые валюты"""
    RUB = "RUB"  # Рубль
    USD = "USD"  # Доллар
    EUR = "EUR"  # Евро
    KZT = "KZT"  # Тенге


class PaymentTerms(str, Enum):
    """Условия оплаты"""
    IMMEDIATE = "immediate"  # Сразу
    NET_10 = "net_10"  # 10 дней
    NET_30 = "net_30"  # 30 дней
    NET_60 = "net_60"  # 60 дней
    NET_90 = "net_90"  # 90 дней


class ExtractedInvoice(BaseModel):
    """Извлеченные данные счета"""
    invoice_number: str
    invoice_date: datetime
    vendor_name: str
    vendor_inn: Optional[str] = None
    vendor_email: str
    
    customer_name: Optional[str] = None
    customer_inn: Optional[str] = None
    
    line_items: List[Dict[str, Any]] = []
    
    subtotal: Decimal = Decimal("0.00")
    vat_amount: Decimal = Decimal("0.00")
    vat_rate: int = 18  # percentage
    total_amount: Decimal = Decimal("0.00")
    
    currency: CurrencyType = CurrencyType.RUB
    payment_terms: PaymentTerms = PaymentTerms.NET_30
    due_date: datetime
    
    description: Optional[str] = None
    attachment_name: Optional[str] = None
    
    confidence: float = Field(ge=0.0, le=1.0)
    extraction_notes: List[str] = []


class InvoiceExtractor:
    """
    Извлечение данных счета из email текста
    Парсит русский и английский текст
    """
    
    # Regex patterns для поиска
    INVOICE_NUMBER_PATTERNS = [
        r'(?:invoice|инв|счет)\s*[№#\s]*:?\s*([A-Za-zА-Яа-яЁё0-9\-]+)',
        r'INV[:\s\-]*([0-9\-]+)',
        r'СЧЁТ[:\s]*([А-Яа-яЁё0-9\-]+)',
    ]
    
    AMOUNT_PATTERNS = [
        r'(?:сумма|итого|total|amount)[:\s]*([0-9\s]+[.,][0-9]{2})',
        r'(\d+[.,]\d{2})\s*(?:₽|RUB|руб)',
        r'(?:\$|USD)?\s*([0-9\s]+[.,][0-9]{2})',
        r'(?:€|EUR)?\s*([0-9\s]+[.,][0-9]{2})',
    ]
    
    VAT_PATTERNS = [
        r'(?:НДС|VAT|ндс)[:\s]*(\d+)%',
        r'(?:НДС|VAT)[:\s]*([0-9\s]+[.,][0-9]{2})',
    ]
    
    DATE_PATTERNS = [
        r'(\d{1,2})[.\s/\-](\d{1,2})[.\s/\-](\d{4})',  # DD.MM.YYYY
        r'(\d{4})[.\s/\-](\d{1,2})[.\s/\-](\d{1,2})',  # YYYY-MM-DD
    ]
    
    PAYMENT_TERMS_MAP = {
        'сразу': PaymentTerms.IMMEDIATE,
        'immediately': PaymentTerms.IMMEDIATE,
        'net 10': PaymentTerms.NET_10,
        '10 дней': PaymentTerms.NET_10,
        'net 30': PaymentTerms.NET_30,
        '30 дней': PaymentTerms.NET_30,
        'net 60': PaymentTerms.NET_60,
        '60 дней': PaymentTerms.NET_60,
        'net 90': PaymentTerms.NET_90,
        '90 дней': PaymentTerms.NET_90,
    }
    
    def __init__(self):
        self.compiled_patterns = {}
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Скомпилировать regex patterns"""
        pattern_groups = {
            'invoice_number': self.INVOICE_NUMBER_PATTERNS,
            'amount': self.AMOUNT_PATTERNS,
            'vat': self.VAT_PATTERNS,
            'date': self.DATE_PATTERNS,
        }
        
        for group_name, patterns in pattern_groups.items():
            self.compiled_patterns[group_name] = [
                re.compile(p, re.IGNORECASE | re.MULTILINE)
                for p in patterns
            ]
    
    def extract(
        self,
        email_subject: str,
        email_body: str,
        from_email: str,
        from_name: Optional[str] = None
    ) -> Optional[ExtractedInvoice]:
        """
        Извлечь данные счета из email
        
        Args:
            email_subject: Subject письма
            email_body: Body письма
            from_email: Email отправителя (vendor)
            from_name: Имя отправителя
            
        Returns:
            ExtractedInvoice или None если не удалось извлечь
        """
        
        try:
            search_text = f"{email_subject}\n{email_body}"
            
            # Извлечь основные поля
            invoice_number = self._extract_invoice_number(search_text)
            if not invoice_number:
                logger.warning("Could not extract invoice number")
                return None
            
            invoice_date = self._extract_invoice_date(search_text)
            if not invoice_date:
                logger.warning("Could not extract invoice date")
                invoice_date = datetime.utcnow()
            
            amount = self._extract_amount(search_text)
            if not amount:
                logger.warning("Could not extract amount")
                return None
            
            vat_rate = self._extract_vat_rate(search_text)
            vat_amount = self._calculate_vat(amount, vat_rate)
            
            payment_terms = self._extract_payment_terms(search_text)
            due_date = self._calculate_due_date(invoice_date, payment_terms)
            
            currency = self._extract_currency(search_text)
            
            # Построить объект
            extracted = ExtractedInvoice(
                invoice_number=invoice_number,
                invoice_date=invoice_date,
                vendor_name=from_name or from_email,
                vendor_email=from_email,
                
                subtotal=amount - vat_amount,
                vat_amount=vat_amount,
                vat_rate=vat_rate,
                total_amount=amount,
                
                currency=currency,
                payment_terms=payment_terms,
                due_date=due_date,
                
                description=email_subject,
                confidence=self._calculate_confidence(search_text),
                extraction_notes=self._collect_notes(search_text)
            )
            
            logger.info(
                f"Extracted invoice: {extracted.invoice_number} "
                f"from {extracted.vendor_email} "
                f"(amount: {extracted.total_amount} {extracted.currency})"
            )
            
            return extracted
        
        except Exception as e:
            logger.error(f"Error extracting invoice: {e}")
            return None
    
    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """Найти номер счета"""
        for pattern in self.compiled_patterns['invoice_number']:
            match = pattern.search(text)
            if match:
                number = match.group(1).strip()
                # Clean up - remove extra whitespace and newlines
                number = ' '.join(number.split())
                # Take only first line if multiline
                number = number.split('\n')[0].strip()
                return number
        return None
    
    def _extract_invoice_date(self, text: str) -> Optional[datetime]:
        """Найти дату счета"""
        for pattern in self.compiled_patterns['date']:
            match = pattern.search(text)
            if match:
                try:
                    groups = match.groups()
                    # Попробовать разные форматы
                    if len(groups[0]) == 4:  # YYYY
                        return datetime(int(groups[0]), int(groups[1]), int(groups[2]))
                    else:  # DD.MM.YYYY
                        return datetime(int(groups[2]), int(groups[1]), int(groups[0]))
                except:
                    continue
        return None
    
    def _extract_amount(self, text: str) -> Optional[Decimal]:
        """Найти сумму счета"""
        for pattern in self.compiled_patterns['amount']:
            match = pattern.search(text)
            if match:
                try:
                    amount_str = match.group(1).replace(' ', '').replace(',', '.')
                    return Decimal(amount_str)
                except:
                    continue
        return None
    
    def _extract_vat_rate(self, text: str) -> int:
        """Найти ставку НДС (по умолчанию 18%)"""
        for pattern in self.compiled_patterns['vat']:
            match = pattern.search(text)
            if match:
                try:
                    rate = int(match.group(1))
                    if 0 <= rate <= 100:
                        return rate
                except:
                    continue
        return 18  # Default VAT rate in Russia
    
    def _calculate_vat(self, amount: Decimal, vat_rate: int) -> Decimal:
        """Рассчитать НДС"""
        return (amount * Decimal(vat_rate)) / Decimal(100 + vat_rate)
    
    def _extract_payment_terms(self, text: str) -> PaymentTerms:
        """Найти условия оплаты"""
        text_lower = text.lower()
        
        for keyword, term in self.PAYMENT_TERMS_MAP.items():
            if keyword in text_lower:
                return term
        
        return PaymentTerms.NET_30  # Default
    
    def _calculate_due_date(
        self,
        invoice_date: datetime,
        payment_terms: PaymentTerms
    ) -> datetime:
        """Рассчитать срок оплаты"""
        days_map = {
            PaymentTerms.IMMEDIATE: 0,
            PaymentTerms.NET_10: 10,
            PaymentTerms.NET_30: 30,
            PaymentTerms.NET_60: 60,
            PaymentTerms.NET_90: 90,
        }
        
        days = days_map.get(payment_terms, 30)
        return invoice_date + timedelta(days=days)
    
    def _extract_currency(self, text: str) -> CurrencyType:
        """Определить валюту"""
        text_lower = text.lower()
        
        if any(s in text_lower for s in ['₽', 'rub', 'руб', 'рублей']):
            return CurrencyType.RUB
        elif any(s in text_lower for s in ['$', 'usd', 'доллар']):
            return CurrencyType.USD
        elif any(s in text_lower for s in ['€', 'eur', 'евро']):
            return CurrencyType.EUR
        elif any(s in text_lower for s in ['₸', 'kzt', 'тенге']):
            return CurrencyType.KZT
        
        return CurrencyType.RUB  # Default
    
    def _calculate_confidence(self, text: str) -> float:
        """Рассчитать confidence извлечения"""
        confidence = 0.5
        
        # Boost за ключевые слова
        keywords = ['инвойс', 'invoice', 'счет', 'счёт', 'НДС', 'vat']
        for keyword in keywords:
            if keyword.lower() in text.lower():
                confidence += 0.1
        
        # Max confidence
        return min(confidence, 1.0)
    
    def _collect_notes(self, text: str) -> List[str]:
        """Собрать заметки об извлечении"""
        notes = []
        
        # Проверить на потенциальные проблемы
        if len(text) < 100:
            notes.append("Short email text - extraction may be inaccurate")
        
        if 'draft' in text.lower() or 'sample' in text.lower():
            notes.append("Email mentions draft/sample - verify before processing")
        
        if 'no invoice' in text.lower():
            notes.append("Email explicitly states no invoice")
        
        return notes
