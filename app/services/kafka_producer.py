"""
Kafka Producer Service
Асинхронный producer для публикации email events в Kafka
Batch publishing с partitioning по from_email
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from aiokafka import AIOKafkaProducer
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class KafkaConfig(BaseModel):
    """Конфиг для Kafka"""
    bootstrap_servers: List[str] = Field(
        default=["localhost:9092"],
        description="Kafka broker addresses"
    )
    topic: str = Field(default="emails.raw", description="Topic name")
    batch_size: int = Field(default=100, description="Batch size for publishing")
    batch_timeout_seconds: int = Field(default=5, description="Batch timeout")
    compression_type: str = Field(default="gzip", description="Compression: gzip, snappy, lz4")
    acks: str = Field(default="all", description="Acks: 0, 1, all")


class EmailEvent(BaseModel):
    """Event для публикации в Kafka"""
    event_id: str = Field(..., description="Unique event ID")
    timestamp: str = Field(..., description="Event timestamp")
    source: str = Field(default="imap", description="Event source")
    email_data: Dict[str, Any] = Field(..., description="Email data from IMAP")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class KafkaEmailProducer:
    """
    Асинхронный Kafka producer для email events
    Поддержка batch publishing и partitioning
    """
    
    def __init__(self, config: KafkaConfig):
        self.config = config
        self.producer: Optional[AIOKafkaProducer] = None
        self.batch: List[EmailEvent] = []
        self.batch_timer: Optional[asyncio.Task] = None
        self.stats = {
            'events_published': 0,
            'batches_sent': 0,
            'errors': 0,
            'total_bytes': 0
        }
        self.is_running = False
    
    async def init(self) -> bool:
        """Инициализировать producer"""
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.config.bootstrap_servers,
                compression_type=self.config.compression_type,
                acks=self.config.acks,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                max_batch_size=1000000  # 1MB
            )
            
            await self.producer.start()
            self.is_running = True
            logger.info(f"✅ Kafka producer initialized for topic: {self.config.topic}")
            logger.info(f"   Bootstrap servers: {self.config.bootstrap_servers}")
            logger.info(f"   Batch: {self.config.batch_size} events or {self.config.batch_timeout_seconds}s")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to initialize Kafka producer: {e}")
            return False
    
    async def close(self):
        """Закрыть producer"""
        if self.batch_timer and not self.batch_timer.done():
            self.batch_timer.cancel()
            try:
                await self.batch_timer
            except asyncio.CancelledError:
                pass
        
        if self.producer:
            # Отправить оставшиеся события
            if self.batch:
                logger.info(f"📤 Flushing {len(self.batch)} remaining events before shutdown...")
                await self._flush_batch()
            
            await self.producer.stop()
            self.is_running = False
            logger.info("✅ Kafka producer closed")
    
    async def publish(self, email_data: Dict[str, Any]) -> bool:
        """
        Добавить email event в batch для публикации
        
        Args:
            email_data: Raw email data from IMAP
            
        Returns:
            True если успешно добавлено в batch
        """
        try:
            import uuid
            
            # Создать event
            event = EmailEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow().isoformat(),
                email_data=email_data,
                metadata={
                    'source_host': self.config.bootstrap_servers[0] if self.config.bootstrap_servers else 'unknown',
                    'from_email': email_data.get('from_email', 'unknown'),
                    'batch_size': self.config.batch_size
                }
            )
            
            # Добавить в batch
            self.batch.append(event)
            
            logger.debug(f"📥 Added to batch: {event.event_id} (batch size: {len(self.batch)})")
            
            # Проверить размер batch
            if len(self.batch) >= self.config.batch_size:
                logger.info(f"📦 Batch size limit reached ({len(self.batch)} events), flushing...")
                await self._flush_batch()
            
            # Запустить таймер если это первое событие
            elif len(self.batch) == 1:
                self._start_batch_timer()
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Error publishing event: {e}")
            self.stats['errors'] += 1
            return False
    
    def _start_batch_timer(self):
        """Запустить таймер для отправки batch по timeout"""
        async def timeout_handler():
            try:
                await asyncio.sleep(self.config.batch_timeout_seconds)
                if self.batch and self.is_running:
                    logger.info(f"⏱️ Batch timeout ({self.config.batch_timeout_seconds}s), flushing {len(self.batch)} events...")
                    await self._flush_batch()
            except asyncio.CancelledError:
                pass
        
        if self.batch_timer and not self.batch_timer.done():
            self.batch_timer.cancel()
        
        self.batch_timer = asyncio.create_task(timeout_handler())
    
    async def _flush_batch(self):
        """Отправить batch в Kafka"""
        if not self.batch or not self.producer:
            return
        
        try:
            batch_to_send = self.batch.copy()
            self.batch = []
            
            # Cancel timer
            if self.batch_timer and not self.batch_timer.done():
                self.batch_timer.cancel()
            
            logger.info(f"📤 Flushing batch of {len(batch_to_send)} emails to Kafka topic: {self.config.topic}")
            
            # Отправить каждое событие
            successful = 0
            for event in batch_to_send:
                try:
                    # Partition key = from_email (for ordering within sender)
                    partition_key = (
                        event.email_data.get('from_email', 'unknown')
                        .encode('utf-8')
                    )
                    
                    future = await self.producer.send_and_wait(
                        self.config.topic,
                        value=event.dict(),
                        key=partition_key
                    )
                    
                    message_size = len(json.dumps(event.dict()).encode('utf-8'))
                    self.stats['total_bytes'] += message_size
                    self.stats['events_published'] += 1
                    successful += 1
                
                except Exception as e:
                    logger.error(f"❌ Error sending event {event.event_id}: {e}")
                    self.stats['errors'] += 1
            
            self.stats['batches_sent'] += 1
            logger.info(
                f"✅ Batch sent: {successful}/{len(batch_to_send)} events, "
                f"total {self.stats['total_bytes']} bytes"
            )
        
        except Exception as e:
            logger.error(f"❌ Error flushing batch: {e}")
            self.stats['errors'] += 1
            # Re-add to batch for retry
            self.batch.extend(batch_to_send)
    
    async def publish_batch(self, emails: List[Dict[str, Any]]) -> int:
        """
        Опубликовать список emails
        
        Returns:
            Количество успешно опубликованных
        """
        count = 0
        for email_data in emails:
            if await self.publish(email_data):
                count += 1
        
        logger.info(f"📧 Published batch: {count}/{len(emails)} emails")
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Получить статистику producer"""
        return {
            'running': self.is_running,
            'events_published': self.stats['events_published'],
            'batches_sent': self.stats['batches_sent'],
            'errors': self.stats['errors'],
            'total_bytes': self.stats['total_bytes'],
            'pending_batch_size': len(self.batch),
            'batch_config': {
                'max_size': self.config.batch_size,
                'timeout_seconds': self.config.batch_timeout_seconds,
                'compression': self.config.compression_type
            }
        }
