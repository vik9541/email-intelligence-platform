"""
Ollama HTTP Client Service
Асинхронный клиент для Ollama API с retry, pooling, timeout
"""

import aiohttp
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)


class OllamaClient:
    """
    Асинхронный HTTP клиент для Ollama API
    Поддержка retry, connection pooling, timeout
    """
    
    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "mistral:7b",
        timeout: int = 30,
        max_retries: int = 3,
        pool_size: int = 10
    ):
        self.host = host
        self.model = model
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.max_retries = max_retries
        self.pool_size = pool_size
        self.session: Optional[aiohttp.ClientSession] = None
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'total_time_ms': 0
        }
    
    async def init(self):
        """Инициализировать HTTP сессию с connection pooling"""
        connector = aiohttp.TCPConnector(
            limit=self.pool_size,
            limit_per_host=self.pool_size // 2,
            ttl_dns_cache=300
        )
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=self.timeout
        )
        logger.info(f"✅ Ollama client initialized: {self.host}/{self.model}")
    
    async def close(self):
        """Закрыть HTTP сессию"""
        if self.session:
            await self.session.close()
            logger.info("🛑 Ollama client session closed")
    
    async def health_check(self) -> bool:
        """
        Проверить доступность Ollama
        
        Returns:
            True если Ollama доступен
        """
        try:
            async with self.session.get(
                f"{self.host}/api/tags",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                return resp.status == 200
        except Exception as e:
            logger.warning(f"⚠️ Ollama health check failed: {e}")
            return False
    
    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 500,
        retry_count: int = 0
    ) -> Optional[str]:
        """
        Запросить completion у Ollama
        
        Args:
            prompt: User prompt
            system: System prompt (опционально)
            temperature: 0.0-1.0 (lower = more deterministic)
            max_tokens: Max tokens in response
            retry_count: Internal retry counter
            
        Returns:
            Generated text или None если ошибка
        """
        
        if retry_count >= self.max_retries:
            logger.error(f"❌ Max retries ({self.max_retries}) reached for Ollama")
            return None
        
        try:
            import time
            start = time.time()
            
            # Построить request
            messages = []
            
            if system:
                messages.append({
                    "role": "system",
                    "content": system
                })
            
            messages.append({
                "role": "user",
                "content": prompt
            })
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "stream": False,
                "num_predict": max_tokens
            }
            
            # Отправить запрос
            async with self.session.post(
                f"{self.host}/api/chat",
                json=payload
            ) as resp:
                if resp.status != 200:
                    logger.error(f"❌ Ollama error: {resp.status}")
                    
                    # Retry с exponential backoff
                    wait_time = 2 ** retry_count
                    logger.info(f"🔄 Retrying in {wait_time}s (attempt {retry_count + 1})")
                    await asyncio.sleep(wait_time)
                    
                    return await self.complete(
                        prompt=prompt,
                        system=system,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        retry_count=retry_count + 1
                    )
                
                result = await resp.json()
                
                # Extract text from response
                text = result.get("message", {}).get("content", "")
                
                # Update stats
                elapsed_ms = (time.time() - start) * 1000
                self.stats['total_requests'] += 1
                self.stats['successful'] += 1
                self.stats['total_time_ms'] += elapsed_ms
                
                logger.debug(f"✅ Ollama completion: {len(text)} chars in {elapsed_ms:.1f}ms")
                
                return text
        
        except asyncio.TimeoutError:
            logger.warning(f"⏱️ Ollama timeout (attempt {retry_count + 1})")
            await asyncio.sleep(2 ** retry_count)
            return await self.complete(
                prompt=prompt,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
                retry_count=retry_count + 1
            )
        
        except Exception as e:
            logger.error(f"❌ Ollama request failed: {e}")
            self.stats['failed'] += 1
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику запросов"""
        avg_time = (
            self.stats['total_time_ms'] / self.stats['successful']
            if self.stats['successful'] > 0
            else 0
        )
        
        success_rate = (
            self.stats['successful'] / self.stats['total_requests'] * 100
            if self.stats['total_requests'] > 0
            else 0
        )
        
        return {
            'total_requests': self.stats['total_requests'],
            'successful': self.stats['successful'],
            'failed': self.stats['failed'],
            'avg_time_ms': round(avg_time, 1),
            'success_rate': round(success_rate, 1)
        }
    
    def reset_stats(self):
        """Сбросить статистику"""
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'total_time_ms': 0
        }
        logger.info("📊 Ollama stats reset")
