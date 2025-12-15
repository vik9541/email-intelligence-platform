"""
Embedding & RAG Service
Векторные embeddings + similarity search через pgvector
"""

import logging
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Embedding service для RAG (Retrieval-Augmented Generation)
    Использует pgvector для similarity search
    """
    
    def __init__(self, db_service, ollama_client):
        self.db = db_service
        self.ollama = ollama_client
        self.embedding_model = "nomic-embed-text:latest"
        self.embedding_dimensions = 768  # nomic-embed-text dimensions
    
    async def embed_text(self, text: str) -> Optional[List[float]]:
        """
        Получить embedding для текста
        
        Args:
            text: Текст для embedding (email subject + body)
            
        Returns:
            Vector (768 dimensions) или None если ошибка
        """
        try:
            # Truncate text если слишком длинный (max 8192 tokens)
            text = text[:8000]
            
            # Использовать встроенный embedding endpoint Ollama
            import aiohttp
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": self.embedding_model,
                    "prompt": text
                }
                
                async with session.post(
                    f"{self.ollama.host}/api/embeddings",
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status != 200:
                        logger.error(f"❌ Embedding error: {resp.status}")
                        return None
                    
                    result = await resp.json()
                    embedding = result.get("embedding")
                    
                    if embedding and len(embedding) == self.embedding_dimensions:
                        logger.debug(f"✅ Embedded text: {len(text)} chars → {len(embedding)} dims")
                        return embedding
                    
                    logger.error(f"❌ Invalid embedding dimensions: {len(embedding) if embedding else 0}")
                    return None
        
        except Exception as e:
            logger.error(f"❌ Embedding request failed: {e}")
            return None
    
    async def find_similar_emails(
        self,
        email_text: str,
        k: int = 3,
        threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Найти похожие письма используя vector search
        
        Args:
            email_text: Текст email для поиска (subject + body)
            k: Количество похожих примеров
            threshold: Минимальный similarity score (0.0-1.0)
            
        Returns:
            List of similar emails с их классификацией
        """
        try:
            # Получить embedding для входящего письма
            query_embedding = await self.embed_text(email_text)
            
            if not query_embedding:
                logger.warning("⚠️ Failed to embed query text")
                return []
            
            # Выполнить vector similarity search в PostgreSQL
            # NOTE: Требует pgvector extension в PostgreSQL
            async with self.db.get_session() as session:
                from sqlalchemy import text
                
                # Преобразовать embedding в PostgreSQL array format
                embedding_str = f"[{','.join(map(str, query_embedding))}]"
                
                # Raw SQL для vector search в pgvector
                # Использует оператор <=> для cosine distance
                sql = """
                    SELECT 
                        id,
                        message_id,
                        from_email,
                        subject,
                        body_text,
                        category,
                        confidence_score,
                        received_at,
                        1 - (embedding <=> :embedding::vector) as similarity
                    FROM emails
                    WHERE category IS NOT NULL
                    AND embedding IS NOT NULL
                    AND 1 - (embedding <=> :embedding::vector) > :threshold
                    ORDER BY similarity DESC
                    LIMIT :k
                """
                
                result = await session.execute(
                    text(sql),
                    {
                        "embedding": embedding_str,
                        "threshold": threshold,
                        "k": k
                    }
                )
                
                rows = result.fetchall()
                
                similar_emails = []
                for row in rows:
                    similar_emails.append({
                        'id': row[0],
                        'message_id': row[1],
                        'from_email': row[2],
                        'subject': row[3],
                        'body_text': row[4][:200],  # First 200 chars
                        'category': row[5],
                        'confidence': row[6],
                        'received_at': row[7],
                        'similarity': round(row[8], 3)
                    })
                
                logger.info(f"📊 Found {len(similar_emails)} similar emails (threshold={threshold})")
                return similar_emails
        
        except Exception as e:
            logger.error(f"❌ Similarity search failed: {e}")
            return []
    
    async def store_embedding(
        self,
        email_id: int,
        embedding: List[float]
    ) -> bool:
        """
        Сохранить embedding в БД для будущего RAG
        
        Args:
            email_id: ID письма в БД
            embedding: Vector embedding
            
        Returns:
            True если успешно сохранено
        """
        try:
            async with self.db.get_session() as session:
                from sqlalchemy import text
                
                embedding_str = f"[{','.join(map(str, embedding))}]"
                
                sql = """
                    UPDATE emails
                    SET embedding = :embedding::vector
                    WHERE id = :email_id
                """
                
                await session.execute(
                    text(sql),
                    {
                        "embedding": embedding_str,
                        "email_id": email_id
                    }
                )
                
                await session.commit()
                
                logger.debug(f"✅ Stored embedding for email {email_id}")
                return True
        
        except Exception as e:
            logger.error(f"❌ Failed to store embedding: {e}")
            return False
    
    async def embed_and_store(
        self,
        email_id: int,
        email_text: str
    ) -> bool:
        """
        Создать embedding и сохранить в БД
        
        Args:
            email_id: ID письма
            email_text: Текст письма (subject + body)
            
        Returns:
            True если успешно
        """
        embedding = await self.embed_text(email_text)
        
        if not embedding:
            return False
        
        return await self.store_embedding(email_id, embedding)
