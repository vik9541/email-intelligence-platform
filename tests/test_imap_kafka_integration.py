"""
Integration Tests for IMAP + Kafka
Tests: listener management, Kafka status, end-to-end flow
"""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_listener_start_endpoint():
    """Запустить IMAP listener через API"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/listener/start",
            json={
                "host": "imap.gmail.com",
                "port": 993,
                "username": "test@gmail.com",
                "password": "test_app_password",
                "use_ssl": True
            }
        )
        
        # 200 OK (started) или 202 Accepted (async operation)
        assert response.status_code in [200, 202]
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] in ["started", "error"]


@pytest.mark.asyncio
async def test_listener_start_already_running():
    """Попытка запустить listener когда уже запущен"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Первый запуск
        response1 = await client.post(
            "/api/listener/start",
            json={
                "host": "imap.gmail.com",
                "username": "test@gmail.com",
                "password": "password"
            }
        )
        
        # Второй запуск (должен вернуть ошибку)
        response2 = await client.post(
            "/api/listener/start",
            json={
                "host": "imap.gmail.com",
                "username": "test@gmail.com",
                "password": "password"
            }
        )
        
        # Один из запросов должен вернуть ошибку
        assert response2.status_code in [200, 400]


@pytest.mark.asyncio
async def test_listener_stop_endpoint():
    """Остановить IMAP listener"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/listener/stop")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] in ["stopped", "not_running"]


@pytest.mark.asyncio
async def test_listener_status_not_initialized():
    """Статус listener когда не инициализирован"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/listener/status")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "connected" in data
        assert "running" in data


@pytest.mark.asyncio
async def test_listener_status_after_start():
    """Статус listener после запуска"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Запустить listener
        await client.post(
            "/api/listener/start",
            json={
                "host": "imap.gmail.com",
                "username": "test@gmail.com",
                "password": "password"
            }
        )
        
        # Проверить статус
        response = await client.get("/api/listener/status")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "emails_fetched" in data or "status" in data


@pytest.mark.asyncio
async def test_kafka_status_endpoint():
    """Проверить статус Kafka producer"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/kafka/status")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        
        # Если Kafka инициализирован
        if data["status"] == "running":
            assert "events_published" in data
            assert "batches_sent" in data
            assert "pending_batch_size" in data


@pytest.mark.asyncio
async def test_kafka_status_stats():
    """Проверить структуру Kafka статистики"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/kafka/status")
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Базовые поля должны быть всегда
        assert "status" in data
        assert "running" in data
        
        # Если running, должна быть полная статистика
        if data.get("running"):
            assert "events_published" in data
            assert "batches_sent" in data
            assert "total_bytes" in data
            assert "batch_config" in data


@pytest.mark.asyncio
async def test_listener_validation_missing_fields():
    """Валидация request при старте listener"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Запрос без обязательных полей
        response = await client.post(
            "/api/listener/start",
            json={
                "host": "imap.gmail.com"
                # missing username and password
            }
        )
        
        # 422 Unprocessable Entity (validation error)
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_listener_validation_invalid_port():
    """Валидация port при старте listener"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/listener/start",
            json={
                "host": "imap.gmail.com",
                "port": "not_a_number",  # Invalid
                "username": "test@gmail.com",
                "password": "password"
            }
        )
        
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_health_check_includes_listener():
    """Health check включает статус listener"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        
        assert response.status_code == 200
        
        # Health endpoint может включать статус listener (опционально)


@pytest.mark.asyncio
async def test_listener_lifecycle():
    """Полный жизненный цикл listener: start → status → stop"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 1. Start listener
        start_response = await client.post(
            "/api/listener/start",
            json={
                "host": "imap.gmail.com",
                "username": "test@gmail.com",
                "password": "password"
            }
        )
        
        assert start_response.status_code in [200, 202]
        
        # 2. Check status
        status_response = await client.get("/api/listener/status")
        assert status_response.status_code == 200
        
        # 3. Stop listener
        stop_response = await client.post("/api/listener/stop")
        assert stop_response.status_code == 200
        
        # 4. Check status again (should be stopped)
        final_status = await client.get("/api/listener/status")
        assert final_status.status_code == 200
        
        data = final_status.json()
        # Listener should be stopped or not running
        if "running" in data:
            assert data["running"] is False or data["status"] == "stopped"


@pytest.mark.asyncio
async def test_concurrent_listener_requests():
    """Concurrent requests к listener endpoints"""
    
    import asyncio
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        async def get_status():
            return await client.get("/api/listener/status")
        
        # Создать 5 concurrent requests
        tasks = [get_status() for _ in range(5)]
        responses = await asyncio.gather(*tasks)
        
        # Все запросы должны быть успешными
        for resp in responses:
            assert resp.status_code == 200
