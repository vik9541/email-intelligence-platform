"""
Rules-Based Email Classifier
Быстрая классификация email на основе keyword/pattern/sender matching
Target: <100ms latency, >85% accuracy, 70% coverage
"""

import time
import logging
from typing import Optional, Dict, Tuple
from collections import Counter
from datetime import datetime

from app.models.email_models import EmailDocument, Classification, EmailCategory
from app.services.rules_loader import RulesConfiguration

logger = logging.getLogger(__name__)


class RulesEngine:
    """
    Быстрый классификатор на основе правил
    
    Использует 3 типа проверок:
    - Keyword matching (30% weight)
    - Pattern matching via regex (50% weight)
    - Sender domain matching (20% weight)
    
    Performance: <100ms per email
    Accuracy: >85% for covered categories
    Coverage: ~70% of all emails with confidence >0.85
    """
    
    def __init__(self, config: RulesConfiguration):
        """
        Args:
            config: RulesConfiguration с загруженными правилами
        """
        self.config = config
        
        # Статистика
        self.stats = {
            'total_classified': 0,
            'total_high_confidence': 0,  # confidence > 0.85
            'confidence_scores': {},  # category -> List[float]
            'category_counts': {},  # category -> count
            'processing_times': [],  # List[float] ms
        }
        
        logger.info(
            f"✅ RulesEngine initialized with {len(config.list_categories())} categories"
        )
    
    def classify(self, email: EmailDocument) -> Optional[Classification]:
        """
        Классифицировать письмо по правилам
        
        Args:
            email: EmailDocument для классификации
            
        Returns:
            Classification объект или None если не удалось классифицировать
        """
        start_time = time.time()
        
        try:
            # Подготовить текст для поиска
            search_text = self._prepare_text(email)
            
            # Проверить каждую категорию
            category_scores: Dict[str, float] = {}
            
            for category in self.config.list_categories():
                score = self._score_category(category, email, search_text)
                if score > 0:
                    category_scores[category] = score
            
            # Если нет совпадений - вернуть None
            if not category_scores:
                logger.debug(f"No category matches for email {email.message_id}")
                return None
            
            # Найти лучшую категорию
            best_category = max(category_scores, key=category_scores.get)
            raw_confidence = category_scores[best_category]
            
            # Применить базовый confidence для категории
            base_confidence = self.config.get_confidence_base(best_category)
            final_confidence = min(raw_confidence * base_confidence, 1.0)
            
            # Обновить статистику
            processing_time_ms = (time.time() - start_time) * 1000
            self._update_stats(best_category, final_confidence, processing_time_ms)
            
            # Логирование
            logger.info(
                f"📧 Classified email {email.message_id[:8]}... "
                f"from {email.from_email}: "
                f"{best_category.upper()} ({final_confidence:.2f}) "
                f"in {processing_time_ms:.1f}ms"
            )
            
            # Создать Classification объект
            return Classification(
                category=EmailCategory(best_category),
                confidence=final_confidence,
                priority=self.config.get_priority(best_category),
                reasoning=self._generate_reasoning(
                    best_category, 
                    raw_confidence,
                    processing_time_ms
                )
            )
        
        except Exception as e:
            logger.error(f"❌ Error classifying email: {e}", exc_info=True)
            return None
    
    def _prepare_text(self, email: EmailDocument) -> str:
        """
        Подготовить текст для поиска
        
        Объединяет subject + body в один текст
        
        Args:
            email: EmailDocument
            
        Returns:
            Подготовленный текст для поиска
        """
        text_parts = [
            email.subject or "",
            email.body_text or "",
        ]
        
        # Объединить части
        text = " ".join(text_parts)
        
        # Применить case folding если нужно
        if self.config.get_setting('case_insensitive', True):
            text = text.lower()
        
        return text
    
    def _score_category(
        self,
        category: str,
        email: EmailDocument,
        search_text: str
    ) -> float:
        """
        Вычислить score для категории (0.0 - 1.0)
        
        Комбинирует:
        - Keyword matching (30% weight)
        - Pattern matching (50% weight)
        - Sender matching (20% weight)
        
        Args:
            category: Название категории
            email: EmailDocument
            search_text: Подготовленный текст для поиска
            
        Returns:
            Score от 0.0 до 1.0
        """
        # Проверить exclude keywords (если найден - вернуть 0)
        exclude_keywords = self.config.get_exclude_keywords(category)
        for exclude_kw in exclude_keywords:
            if exclude_kw in search_text:
                logger.debug(
                    f"Excluded {category} for email due to keyword '{exclude_kw}'"
                )
                return 0.0
        
        # Считать scores для каждого типа проверки
        keyword_score = self._score_keywords(category, search_text)
        pattern_score = self._score_patterns(category, search_text)
        sender_score = self._score_sender(category, email.from_email)
        
        # Взвешенная сумма
        weights = {
            'keyword': self.config.get_setting('keyword_weight', 0.3),
            'pattern': self.config.get_setting('pattern_weight', 0.5),
            'sender': self.config.get_setting('sender_weight', 0.2)
        }
        
        total_score = (
            keyword_score * weights['keyword'] +
            pattern_score * weights['pattern'] +
            sender_score * weights['sender']
        )
        
        logger.debug(
            f"{category}: keyword={keyword_score:.2f} ({weights['keyword']*100}%), "
            f"pattern={pattern_score:.2f} ({weights['pattern']*100}%), "
            f"sender={sender_score:.2f} ({weights['sender']*100}%) "
            f"-> total={total_score:.2f}"
        )
        
        return total_score
    
    def _score_keywords(self, category: str, text: str) -> float:
        """
        Score на основе keyword matching
        
        Args:
            category: Название категории
            text: Текст для поиска
            
        Returns:
            Score от 0.0 до 1.0
        """
        keywords = self.config.get_keywords(category)
        if not keywords:
            return 0.0
        
        # Ограничить количество проверяемых keywords
        max_keywords = self.config.get_setting('max_keywords_check', 50)
        keywords_to_check = keywords[:max_keywords]
        
        # Считать совпадения
        matches = 0
        for keyword in keywords_to_check:
            if keyword in text:
                matches += 1
        
        # Score: sqrt(matches / total) для учета множественных совпадений
        # но не давать слишком большой вес при большом количестве keywords
        import math
        score = math.sqrt(matches / len(keywords_to_check))
        
        return min(score, 1.0)
    
    def _score_patterns(self, category: str, text: str) -> float:
        """
        Score на основе regex patterns
        
        Args:
            category: Название категории
            text: Текст для поиска
            
        Returns:
            Score от 0.0 до 1.0
        """
        patterns = self.config.get_patterns(category)
        if not patterns:
            return 0.0
        
        # Ограничить количество проверяемых patterns
        max_patterns = self.config.get_setting('max_patterns_check', 20)
        patterns_to_check = patterns[:max_patterns]
        
        matches = 0
        for pattern in patterns_to_check:
            if pattern.search(text):
                matches += 1
        
        # Score: matches / pattern_count
        # Patterns более точные чем keywords, поэтому линейная зависимость
        score = matches / len(patterns_to_check)
        
        return min(score, 1.0)
    
    def _score_sender(self, category: str, from_email: str) -> float:
        """
        Score на основе sender domain
        
        Args:
            category: Название категории
            from_email: Email отправителя
            
        Returns:
            Score: 1.0 если match, 0.0 если нет
        """
        if not from_email:
            return 0.0
        
        sender_patterns = self.config.get_sender_patterns(category)
        if not sender_patterns:
            return 0.0
        
        # Проверить каждый pattern
        for pattern in sender_patterns:
            if pattern.search(from_email):
                return 1.0
        
        return 0.0
    
    def _generate_reasoning(
        self,
        category: str,
        confidence: float,
        processing_time_ms: float
    ) -> str:
        """
        Сгенерировать объяснение классификации
        
        Args:
            category: Категория
            confidence: Confidence score
            processing_time_ms: Время обработки в ms
            
        Returns:
            Строка с объяснением
        """
        return (
            f"Fast rules classifier: matched '{category}' category "
            f"with {confidence:.2f} confidence "
            f"(processed in {processing_time_ms:.1f}ms)"
        )
    
    def _update_stats(
        self,
        category: str,
        confidence: float,
        processing_time_ms: float
    ):
        """
        Обновить статистику
        
        Args:
            category: Классифицированная категория
            confidence: Confidence score
            processing_time_ms: Время обработки
        """
        self.stats['total_classified'] += 1
        
        # Считать high confidence classifications
        if confidence > self.config.get_setting('high_confidence_threshold', 0.85):
            self.stats['total_high_confidence'] += 1
        
        # Сохранить confidence scores
        if category not in self.stats['confidence_scores']:
            self.stats['confidence_scores'][category] = []
        self.stats['confidence_scores'][category].append(confidence)
        
        # Считать по категориям
        self.stats['category_counts'][category] = (
            self.stats['category_counts'].get(category, 0) + 1
        )
        
        # Сохранить processing time
        self.stats['processing_times'].append(processing_time_ms)
    
    def get_stats(self) -> Dict:
        """
        Получить статистику классификации
        
        Returns:
            Dict со статистикой
        """
        # Вычислить средние confidence scores
        avg_confidence = {}
        for cat, scores in self.stats['confidence_scores'].items():
            if scores:
                avg_confidence[cat] = sum(scores) / len(scores)
        
        # Вычислить средний processing time
        avg_time_ms = 0.0
        if self.stats['processing_times']:
            avg_time_ms = sum(self.stats['processing_times']) / len(self.stats['processing_times'])
        
        # Вычислить coverage (% high confidence)
        coverage_pct = 0.0
        if self.stats['total_classified'] > 0:
            coverage_pct = (
                self.stats['total_high_confidence'] / self.stats['total_classified'] * 100
            )
        
        return {
            'total_classified': self.stats['total_classified'],
            'total_high_confidence': self.stats['total_high_confidence'],
            'coverage_pct': round(coverage_pct, 1),
            'categories': self.stats['category_counts'],
            'avg_confidence_by_category': {
                cat: round(conf, 2) 
                for cat, conf in avg_confidence.items()
            },
            'avg_processing_time_ms': round(avg_time_ms, 1),
            'performance_ok': avg_time_ms < 100,  # Target: <100ms
        }
    
    def reset_stats(self):
        """Сбросить статистику"""
        self.stats = {
            'total_classified': 0,
            'total_high_confidence': 0,
            'confidence_scores': {},
            'category_counts': {},
            'processing_times': [],
        }
        logger.info("📊 Statistics reset")
