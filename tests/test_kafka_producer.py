"""
Unit Tests for Kafka Email Producer
Tests: initialization, batch publishing, partitioning, stats
"""

import pytest
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.kafka_producer import KafkaEmailProducer, KafkaConfig, EmailEvent


@pytest.fixture
def kafka_config():
    """Kafka configuration fixture"""
    return KafkaConfig(
        bootstrap_servers=["localhost:9092"],
        topic="emails.raw",
        batch_size=100,
        batch_timeout_seconds=5,
        compression_type="gzip",
        acks="all"
    )


@pytest.fixture
def kafka_producer(kafka_config):
    """Kafka producer fixture with mocked AIOKafkaProducer"""
    producer = KafkaEmailProducer(kafka_config)
    producer.producer = AsyncMock()
    producer.is_running = True
    return producer


# ==============================================================================
# TEST: Initialization
# ==============================================================================

@pytest.mark.asyncio
async def test_producer_init_success(kafka_config):
    """Успешная инициализация Kafka producer"""
    
    with patch('app.services.kafka_producer.AIOKafkaProducer') as mock_producer_class:
        mock_instance = AsyncMock()
        mock_instance.start = AsyncMock()
        mock_producer_class.return_value = mock_instance
        
        producer = KafkaEmailProducer(kafka_config)
        result = await producer.init()
        
        assert result is True
        assert producer.is_running is True
        mock_instance.start.assert_called_once()


@pytest.mark.asyncio
async def test_producer_init_failure(kafka_config):
    """Ошибка при инициализации"""
    
    with patch('app.services.kafka_producer.AIOKafkaProducer') as mock_producer_class:
        mock_instance = AsyncMock()
        mock_instance.start = AsyncMock(side_effect=Exception("Connection failed"))
        mock_producer_class.return_value = mock_instance
        
        producer = KafkaEmailProducer(kafka_config)
        result = await producer.init()
        
        assert result is False
        assert producer.is_running is False


# ==============================================================================
# TEST: Publishing Single Event
# ==============================================================================

@pytest.mark.asyncio
async def test_publish_single_event(kafka_producer):
    """Опубликовать одиночный email event"""
    
    email_data = {
        'message_id': '<test@example.com>',
        'from_email': 'sender@example.com',
        'to_email': 'receiver@example.com',
        'subject': 'Test Email',
        'imap_id': '1',
        'date': '2025-12-15 10:00:00'
    }
    
    result = await kafka_producer.publish(email_data)
    
    assert result is True
    assert len(kafka_producer.batch) == 1
    assert kafka_producer.batch[0].email_data == email_data


@pytest.mark.asyncio
async def test_publish_creates_valid_event(kafka_producer):
    """Проверить создание валидного EmailEvent"""
    
    email_data = {
        'from_email': 'test@example.com',
        'subject': 'Test',
        'imap_id': '1'
    }
    
    await kafka_producer.publish(email_data)
    
    event = kafka_producer.batch[0]
    assert event.event_id is not None
    assert event.timestamp is not None
    assert event.source == 'imap'
    assert event.email_data == email_data
    assert 'from_email' in event.metadata


# ==============================================================================
# TEST: Batch Publishing
# ==============================================================================

@pytest.mark.asyncio
async def test_publish_batch_auto_flush(kafka_producer):
    """Автоматическая отправка batch при достижении размера"""
    
    kafka_producer.config.batch_size = 2
    kafka_producer.producer.send_and_wait = AsyncMock()
    
    email1 = {'from_email': 'test1@example.com', 'subject': 'Test 1', 'imap_id': '1'}
    email2 = {'from_email': 'test2@example.com', 'subject': 'Test 2', 'imap_id': '2'}
    
    await kafka_producer.publish(email1)
    assert len(kafka_producer.batch) == 1
    
    await kafka_producer.publish(email2)
    # Batch должен быть отправлен
    assert len(kafka_producer.batch) == 0
    assert kafka_producer.stats['batches_sent'] == 1
    assert kafka_producer.stats['events_published'] == 2


@pytest.mark.asyncio
async def test_publish_batch_list(kafka_producer):
    """Опубликовать список emails"""
    
    emails = [
        {'from_email': f'test{i}@example.com', 'subject': f'Test {i}', 'imap_id': str(i)}
        for i in range(5)
    ]
    
    count = await kafka_producer.publish_batch(emails)
    
    assert count == 5
    assert len(kafka_producer.batch) == 5


@pytest.mark.asyncio
async def test_batch_timeout_flush(kafka_producer):
    """Отправка batch по timeout"""
    
    kafka_producer.config.batch_timeout_seconds = 1
    kafka_producer.producer.send_and_wait = AsyncMock()
    
    email = {'from_email': 'test@example.com', 'subject': 'Test', 'imap_id': '1'}
    
    await kafka_producer.publish(email)
    assert len(kafka_producer.batch) == 1
    
    # Ждать timeout
    await asyncio.sleep(1.5)
    
    # Batch должен быть отправлен
    assert len(kafka_producer.batch) == 0


# ==============================================================================
# TEST: Partition Key
# ==============================================================================

@pytest.mark.asyncio
async def test_partition_key_from_email(kafka_producer):
    """Partition key = from_email для ordering"""
    
    kafka_producer.config.batch_size = 1
    kafka_producer.producer.send_and_wait = AsyncMock()
    
    email = {'from_email': 'sender@example.com', 'subject': 'Test', 'imap_id': '1'}
    
    await kafka_producer.publish(email)
    
    # Проверить что send_and_wait вызван с правильным partition key
    call_args = kafka_producer.producer.send_and_wait.call_args
    assert call_args[1]['key'] == b'sender@example.com'


# ==============================================================================
# TEST: Error Handling
# ==============================================================================

@pytest.mark.asyncio
async def test_publish_error_handling(kafka_producer):
    """Обработка ошибок при публикации"""
    
    # Simulate error during event creation
    with patch('uuid.uuid4', side_effect=Exception("UUID generation failed")):
        result = await kafka_producer.publish({'from_email': 'test@example.com'})
        
        assert result is False
        assert kafka_producer.stats['errors'] == 1


@pytest.mark.asyncio
async def test_flush_error_retry(kafka_producer):
    """Retry при ошибке отправки batch"""
    
    kafka_producer.config.batch_size = 1
    kafka_producer.producer.send_and_wait = AsyncMock(side_effect=Exception("Send failed"))
    
    email = {'from_email': 'test@example.com', 'subject': 'Test', 'imap_id': '1'}
    
    await kafka_producer.publish(email)
    
    # События должны остаться в batch для retry
    assert len(kafka_producer.batch) > 0
    assert kafka_producer.stats['errors'] > 0


# ==============================================================================
# TEST: Statistics
# ==============================================================================

@pytest.mark.asyncio
async def test_producer_stats(kafka_producer):
    """Сбор статистики producer"""
    
    kafka_producer.stats['events_published'] = 100
    kafka_producer.stats['batches_sent'] = 5
    kafka_producer.stats['total_bytes'] = 50000
    kafka_producer.batch = [MagicMock(), MagicMock()]
    
    stats = kafka_producer.get_stats()
    
    assert stats['running'] is True
    assert stats['events_published'] == 100
    assert stats['batches_sent'] == 5
    assert stats['total_bytes'] == 50000
    assert stats['pending_batch_size'] == 2
    assert 'batch_config' in stats


# ==============================================================================
# TEST: Close and Flush
# ==============================================================================

@pytest.mark.asyncio
async def test_close_flushes_remaining_events(kafka_producer):
    """Закрытие producer отправляет оставшиеся события"""
    
    kafka_producer.producer.send_and_wait = AsyncMock()
    kafka_producer.producer.stop = AsyncMock()
    
    # Добавить события в batch
    await kafka_producer.publish({'from_email': 'test1@example.com', 'imap_id': '1'})
    await kafka_producer.publish({'from_email': 'test2@example.com', 'imap_id': '2'})
    
    assert len(kafka_producer.batch) == 2
    
    # Закрыть producer
    await kafka_producer.close()
    
    # Batch должен быть отправлен
    assert len(kafka_producer.batch) == 0
    kafka_producer.producer.stop.assert_called_once()


@pytest.mark.asyncio
async def test_close_cancels_timer(kafka_producer):
    """Закрытие producer отменяет batch timer"""
    
    kafka_producer.producer.send_and_wait = AsyncMock()
    kafka_producer.producer.stop = AsyncMock()
    
    # Создать batch с таймером
    await kafka_producer.publish({'from_email': 'test@example.com', 'imap_id': '1'})
    
    assert kafka_producer.batch_timer is not None
    
    await kafka_producer.close()
    
    # Timer должен быть отменен
    assert kafka_producer.batch_timer.done() or kafka_producer.batch_timer.cancelled()


# ==============================================================================
# TEST: Configuration
# ==============================================================================

def test_kafka_config_defaults():
    """Проверить defaults в KafkaConfig"""
    
    config = KafkaConfig()
    
    assert config.bootstrap_servers == ["localhost:9092"]
    assert config.topic == "emails.raw"
    assert config.batch_size == 100
    assert config.batch_timeout_seconds == 5
    assert config.compression_type == "gzip"
    assert config.acks == "all"


def test_kafka_config_custom():
    """Проверить custom конфигурацию"""
    
    config = KafkaConfig(
        bootstrap_servers=["kafka1:9092", "kafka2:9092"],
        topic="custom.topic",
        batch_size=50,
        batch_timeout_seconds=10,
        compression_type="snappy",
        acks="1"
    )
    
    assert config.bootstrap_servers == ["kafka1:9092", "kafka2:9092"]
    assert config.topic == "custom.topic"
    assert config.batch_size == 50
    assert config.compression_type == "snappy"


# ==============================================================================
# TEST: Email Event Model
# ==============================================================================

def test_email_event_creation():
    """Создание EmailEvent"""
    
    import uuid
    
    event = EmailEvent(
        event_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow().isoformat(),
        source="imap",
        email_data={'from': 'test@example.com'},
        metadata={'key': 'value'}
    )
    
    assert event.source == "imap"
    assert event.email_data == {'from': 'test@example.com'}
    assert event.metadata == {'key': 'value'}


def test_email_event_to_dict():
    """Сериализация EmailEvent"""
    
    import uuid
    
    event = EmailEvent(
        event_id=str(uuid.uuid4()),
        timestamp=datetime.utcnow().isoformat(),
        email_data={'test': 'data'}
    )
    
    event_dict = event.dict()
    
    assert 'event_id' in event_dict
    assert 'timestamp' in event_dict
    assert 'source' in event_dict
    assert 'email_data' in event_dict
    assert event_dict['email_data'] == {'test': 'data'}
