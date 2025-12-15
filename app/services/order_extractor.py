"""
Order Extractor Service - Extract structured data from purchase order emails.

Parses Russian and English PO text to extract:
- Order number, line items (SKU, qty, price)
- Delivery date and address
- Priority level
- Customer info
"""

import re
import logging
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class OrderPriority(str, Enum):
    """Приоритет заказа"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class OrderLineItem(BaseModel):
    """Строка в заказе"""
    sku: str
    description: str
    quantity: int
    unit_price: Decimal
    total: Decimal


class ExtractedOrder(BaseModel):
    """Извлеченные данные заказа"""
    order_number: str
    order_date: datetime
    customer_name: str
    customer_email: str
    customer_inn: Optional[str] = None
    
    supplier_name: Optional[str] = None
    supplier_email: Optional[str] = None
    
    line_items: List[OrderLineItem] = []
    
    subtotal: Decimal = Decimal("0.00")
    total_amount: Decimal = Decimal("0.00")
    
    delivery_date: Optional[datetime] = None
    delivery_address: Optional[str] = None
    
    priority: OrderPriority = OrderPriority.NORMAL
    special_instructions: Optional[str] = None
    
    confidence: float = Field(ge=0.0, le=1.0)
    extraction_notes: List[str] = []


class OrderExtractor:
    """
    Извлечение данных заказа из email текста
    Парсит PO, RFQ, order requests
    """
    
    PO_NUMBER_PATTERNS = [
        r'(?:PO|заказ|order)\s*[№#\s]*:?\s*([A-Za-zА-Яа-яЁё0-9\-]+)',
        r'PO[:\s\-]*([0-9\-]+)',
        r'OrderID[:=\s]+([0-9\-]+)',
    ]
    
    SKU_PATTERNS = [
        r'SKU[:\s]*([А-Яа-яЁё0-9\-]+)',
        r'(?:Код|Code)[:=\s]*([А-Яа-яЁё0-9\-]+)',
        r'(?:Артикул|Product)[:\s]*([А-Яа-яЁё0-9\-]+)',
    ]
    
    QUANTITY_PATTERNS = [
        r'(?:Кол-во|Qty|Quantity)[:\s]*(\d+)',
        r'(?:Штук|Units)[:=\s]*(\d+)',
    ]
    
    PRICE_PATTERNS = [
        r'(?:Цена|Price)[:\s]*([0-9.]+)',
        r'(?:Стоимость|Cost)[:=\s]*([0-9.]+)',
    ]
    
    DELIVERY_PATTERNS = [
        r'(?:Доставка|Delivery)[:\s]*(\d{1,2}[.\s/\-]\d{1,2}[.\s/\-]\d{4})',
        r'(?:до|by)\s+(\d{1,2}[.\s/\-]\d{1,2}[.\s/\-]\d{4})',
    ]
    
    def __init__(self):
        self.compiled_patterns = {}
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Скомпилировать regex patterns"""
        pattern_groups = {
            'po_number': self.PO_NUMBER_PATTERNS,
            'sku': self.SKU_PATTERNS,
            'quantity': self.QUANTITY_PATTERNS,
            'price': self.PRICE_PATTERNS,
            'delivery': self.DELIVERY_PATTERNS,
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
    ) -> Optional[ExtractedOrder]:
        """
        Извлечь данные заказа из email
        
        Returns:
            ExtractedOrder или None если не удалось извлечь
        """
        
        try:
            search_text = f"{email_subject}\n{email_body}"
            
            order_number = self._extract_order_number(search_text)
            if not order_number:
                return None
            
            # Извлечь line items
            line_items = self._extract_line_items(search_text)
            
            # Рассчитать totals
            subtotal = sum(item.total for item in line_items)
            
            # Извлечь дату доставки
            delivery_date = self._extract_delivery_date(search_text)
            
            # Определить приоритет
            priority = self._extract_priority(search_text)
            
            extracted = ExtractedOrder(
                order_number=order_number,
                order_date=datetime.utcnow(),
                customer_name=from_name or from_email,
                customer_email=from_email,
                
                line_items=line_items,
                subtotal=subtotal,
                total_amount=subtotal,
                
                delivery_date=delivery_date,
                priority=priority,
                
                confidence=self._calculate_confidence(search_text),
                extraction_notes=self._collect_notes(line_items)
            )
            
            logger.info(
                f"Extracted order: {extracted.order_number} "
                f"from {extracted.customer_email} "
                f"({len(line_items)} items, {subtotal} total)"
            )
            
            return extracted
        
        except Exception as e:
            logger.error(f"Error extracting order: {e}")
            return None
    
    def _extract_order_number(self, text: str) -> Optional[str]:
        """Найти номер заказа"""
        for pattern in self.compiled_patterns['po_number']:
            match = pattern.search(text)
            if match:
                return match.group(1).strip()
        return None
    
    def _extract_line_items(self, text: str) -> List[OrderLineItem]:
        """Извлечь строки заказа"""
        items = []
        
        # Простой парсинг по строкам содержащим SKU
        lines = text.split('\n')
        
        for line in lines:
            sku_match = None
            for pattern in self.compiled_patterns['sku']:
                sku_match = pattern.search(line)
                if sku_match:
                    break
            
            if not sku_match:
                continue
            
            # Извлечь параметры
            sku = sku_match.group(1).strip()
            
            qty = 1
            for pattern in self.compiled_patterns['quantity']:
                qty_match = pattern.search(line)
                if qty_match:
                    qty = int(qty_match.group(1))
                    break
            
            price = Decimal("0.00")
            for pattern in self.compiled_patterns['price']:
                price_match = pattern.search(line)
                if price_match:
                    price = Decimal(price_match.group(1))
                    break
            
            total = Decimal(qty) * price
            
            item = OrderLineItem(
                sku=sku,
                description=line.strip(),
                quantity=qty,
                unit_price=price,
                total=total
            )
            
            items.append(item)
        
        return items
    
    def _extract_delivery_date(self, text: str) -> Optional[datetime]:
        """Найти дату доставки"""
        for pattern in self.compiled_patterns['delivery']:
            match = pattern.search(text)
            if match:
                try:
                    date_str = match.group(1)
                    # Parse date
                    return datetime.strptime(date_str.replace(' ', '.').replace('/', '.').replace('-', '.'), "%d.%m.%Y")
                except:
                    continue
        return None
    
    def _extract_priority(self, text: str) -> OrderPriority:
        """Определить приоритет заказа"""
        text_lower = text.lower()
        
        if any(w in text_lower for w in ['urgent', 'асап', 'срочно', 'asap']):
            return OrderPriority.URGENT
        elif any(w in text_lower for w in ['high', 'high priority', 'высокий']):
            return OrderPriority.HIGH
        elif any(w in text_lower for w in ['low', 'низкий']):
            return OrderPriority.LOW
        
        return OrderPriority.NORMAL
    
    def _calculate_confidence(self, text: str) -> float:
        """Рассчитать confidence"""
        confidence = 0.5
        
        keywords = ['po', 'заказ', 'order', 'sku', 'qty', 'quantity']
        for keyword in keywords:
            if keyword.lower() in text.lower():
                confidence += 0.1
        
        return min(confidence, 1.0)
    
    def _collect_notes(self, items: List[OrderLineItem]) -> List[str]:
        """Собрать заметки"""
        notes = []
        
        if not items:
            notes.append("No line items extracted - verify manually")
        
        for item in items:
            if item.unit_price == Decimal("0.00"):
                notes.append(f"SKU {item.sku} has no price - verify")
        
        return notes
