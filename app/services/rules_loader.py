"""
Rules Loader Service
Загружает и компилирует правила классификации из YAML файла
"""

import yaml
from typing import Dict, List, Optional, Pattern
import re
from pathlib import Path
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class RuleDefinition(BaseModel):
    """Определение одного правила классификации"""
    priority: int = Field(..., ge=1, le=10)
    confidence_base: float = Field(..., ge=0.0, le=1.0)
    keywords: List[str] = Field(default_factory=list)
    patterns: List[str] = Field(default_factory=list)
    sender_patterns: List[str] = Field(default_factory=list)
    exclude_keywords: List[str] = Field(default_factory=list)


class RulesConfiguration:
    """
    Загрузчик и кэшер правил классификации
    
    Загружает YAML файл с правилами и компилирует regex patterns
    для быстрого поиска
    """
    
    def __init__(self, rules_path: str = "config/classification_rules.yaml"):
        """
        Args:
            rules_path: Путь к YAML файлу с правилами
        """
        self.rules_path = Path(rules_path)
        self.rules: Dict[str, RuleDefinition] = {}
        self.compiled_patterns: Dict[str, Dict[str, List[Pattern]]] = {}
        self.settings: Dict = {}
        self._load_rules()
    
    def _load_rules(self):
        """Загрузить и скомпилировать правила из YAML"""
        try:
            if not self.rules_path.exists():
                raise FileNotFoundError(f"Rules file not found: {self.rules_path}")
            
            with open(self.rules_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            if not config:
                raise ValueError("Empty rules configuration")
            
            # Загрузить settings
            self.settings = config.get('settings', {})
            logger.info(f"Loaded settings: {self.settings}")
            
            # Загрузить каждое правило
            rules_data = config.get('rules', {})
            if not rules_data:
                raise ValueError("No rules found in configuration")
            
            for category, rule_data in rules_data.items():
                try:
                    self.rules[category] = RuleDefinition(**rule_data)
                    self._compile_patterns(category, rule_data)
                except Exception as e:
                    logger.error(f"Error loading rule '{category}': {e}")
                    continue
            
            logger.info(
                f"✅ Loaded {len(self.rules)} classification rules from {self.rules_path}"
            )
            
        except Exception as e:
            logger.error(f"❌ Error loading rules: {e}", exc_info=True)
            raise
    
    def _compile_patterns(self, category: str, rule_data: dict):
        """
        Скомпилировать regex patterns для категории
        
        Args:
            category: Название категории
            rule_data: Данные правила из YAML
        """
        self.compiled_patterns[category] = {
            'patterns': [],
            'sender_patterns': []
        }
        
        # Определить флаги для regex
        flags = re.IGNORECASE if self.settings.get('case_insensitive', True) else 0
        
        # Компилировать body/subject patterns
        for pattern_str in rule_data.get('patterns', []):
            try:
                compiled = re.compile(pattern_str, flags)
                self.compiled_patterns[category]['patterns'].append(compiled)
            except Exception as e:
                logger.warning(
                    f"⚠️ Invalid pattern '{pattern_str}' in {category}: {e}"
                )
        
        # Компилировать sender patterns
        for pattern_str in rule_data.get('sender_patterns', []):
            try:
                compiled = re.compile(pattern_str, flags)
                self.compiled_patterns[category]['sender_patterns'].append(compiled)
            except Exception as e:
                logger.warning(
                    f"⚠️ Invalid sender pattern '{pattern_str}' in {category}: {e}"
                )
        
        logger.debug(
            f"Compiled {len(self.compiled_patterns[category]['patterns'])} patterns "
            f"and {len(self.compiled_patterns[category]['sender_patterns'])} sender patterns "
            f"for {category}"
        )
    
    def get_keywords(self, category: str) -> List[str]:
        """
        Получить keywords для категории
        
        Args:
            category: Название категории
            
        Returns:
            Список keywords (в lowercase если case_insensitive=True)
        """
        if category not in self.rules:
            return []
        
        keywords = self.rules[category].keywords
        
        if self.settings.get('case_insensitive', True):
            return [kw.lower() for kw in keywords]
        
        return keywords
    
    def get_exclude_keywords(self, category: str) -> List[str]:
        """
        Получить exclude keywords для категории
        
        Args:
            category: Название категории
            
        Returns:
            Список exclude keywords
        """
        if category not in self.rules:
            return []
        
        exclude_kw = self.rules[category].exclude_keywords
        
        if self.settings.get('case_insensitive', True):
            return [kw.lower() for kw in exclude_kw]
        
        return exclude_kw
    
    def get_patterns(self, category: str) -> List[Pattern]:
        """
        Получить скомпилированные regex patterns
        
        Args:
            category: Название категории
            
        Returns:
            Список скомпилированных Pattern объектов
        """
        return self.compiled_patterns.get(category, {}).get('patterns', [])
    
    def get_sender_patterns(self, category: str) -> List[Pattern]:
        """
        Получить sender patterns
        
        Args:
            category: Название категории
            
        Returns:
            Список скомпилированных Pattern объектов для sender domain
        """
        return self.compiled_patterns.get(category, {}).get('sender_patterns', [])
    
    def get_confidence_base(self, category: str) -> float:
        """
        Базовый confidence для категории
        
        Args:
            category: Название категории
            
        Returns:
            Базовый confidence score (0.0-1.0)
        """
        if category not in self.rules:
            return self.settings.get('min_confidence', 0.5)
        
        return self.rules[category].confidence_base
    
    def get_priority(self, category: str) -> int:
        """
        Получить приоритет категории
        
        Args:
            category: Название категории
            
        Returns:
            Приоритет (1 = highest, 10 = lowest)
        """
        if category not in self.rules:
            return 10
        
        return self.rules[category].priority
    
    def list_categories(self) -> List[str]:
        """
        Получить список всех категорий
        
        Returns:
            Список названий категорий
        """
        return list(self.rules.keys())
    
    def get_setting(self, key: str, default=None):
        """
        Получить значение настройки
        
        Args:
            key: Ключ настройки
            default: Значение по умолчанию
            
        Returns:
            Значение настройки или default
        """
        return self.settings.get(key, default)
    
    def reload(self):
        """Перезагрузить правила из файла"""
        logger.info(f"🔄 Reloading rules from {self.rules_path}")
        self.rules.clear()
        self.compiled_patterns.clear()
        self.settings.clear()
        self._load_rules()
    
    def validate(self) -> bool:
        """
        Валидация конфигурации правил
        
        Returns:
            True если конфигурация валидна
        """
        try:
            # Проверить наличие категорий
            if not self.rules:
                logger.error("❌ No rules loaded")
                return False
            
            # Проверить веса (должны суммироваться в 1.0)
            keyword_weight = self.settings.get('keyword_weight', 0.3)
            pattern_weight = self.settings.get('pattern_weight', 0.5)
            sender_weight = self.settings.get('sender_weight', 0.2)
            
            total_weight = keyword_weight + pattern_weight + sender_weight
            if abs(total_weight - 1.0) > 0.01:
                logger.warning(
                    f"⚠️ Weights don't sum to 1.0: {total_weight:.2f}"
                )
            
            # Проверить каждое правило
            for category, rule in self.rules.items():
                if rule.confidence_base < 0.0 or rule.confidence_base > 1.0:
                    logger.error(
                        f"❌ Invalid confidence_base for {category}: {rule.confidence_base}"
                    )
                    return False
                
                if not rule.keywords and not rule.patterns and not rule.sender_patterns:
                    logger.warning(
                        f"⚠️ Rule {category} has no keywords, patterns or sender patterns"
                    )
            
            logger.info("✅ Rules configuration is valid")
            return True
            
        except Exception as e:
            logger.error(f"❌ Validation error: {e}")
            return False
