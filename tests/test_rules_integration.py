"""
Integration Tests for Rules Classifier
Tests: API endpoints, database integration, batch processing
"""

import pytest
from httpx import AsyncClient
from app.main import app
from app.models.email_models import EmailCategory
from datetime import datetime
import time


@pytest.mark.asyncio
async def test_classify_endpoint_invoice():
    """
    Тест POST /api/emails/classify для счета
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/emails/classify",
            json={
                "email_id": 1,
                "force_llm": False
            }
        )
        
        assert response.status_code in [200, 404], f"Unexpected status: {response.status_code}"
        
        if response.status_code == 200:
            data = response.json()
            
            # Проверить структуру ответа
            assert "category" in data
            assert "confidence" in data
            assert "reasoning" in data
            assert "processing_time_ms" in data
            
            # Проверить валидность значений
            assert data["category"] in [
                "invoice", "purchase_order", "support", "sales", "hr", "newsletter", "other"
            ]
            assert 0.0 <= data["confidence"] <= 1.0
            assert isinstance(data["processing_time_ms"], (int, float))
            assert data["processing_time_ms"] < 1000  # < 1 second


@pytest.mark.asyncio
async def test_classify_endpoint_with_force_llm():
    """
    Тест forced LLM classification
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/emails/classify",
            json={
                "email_id": 1,
                "force_llm": True
            }
        )
        
        assert response.status_code in [200, 404, 501]
        
        if response.status_code == 200:
            data = response.json()
            assert "category" in data
            # LLM classifier может вернуть другой результат


@pytest.mark.asyncio
async def test_classify_endpoint_invalid_email_id():
    """
    Тест с несуществующим email_id
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/emails/classify",
            json={
                "email_id": 999999999,
                "force_llm": False
            }
        )
        
        assert response.status_code == 404


@pytest.mark.asyncio
async def test_classifier_stats_endpoint():
    """
    Тест GET /api/classifier/stats
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/classifier/stats")
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Проверить структуру ответа
        assert "rules_engine_stats" in data
        assert "rules_loaded" in data
        assert "categories" in data
        
        # Проверить stats
        stats = data["rules_engine_stats"]
        assert "total_classified" in stats
        assert "coverage_pct" in stats
        assert "avg_processing_time_ms" in stats
        assert "performance_ok" in stats
        
        # Проверить categories
        assert isinstance(data["categories"], list)
        assert len(data["categories"]) > 0
        assert "invoice" in data["categories"]


@pytest.mark.asyncio
async def test_classify_batch_performance():
    """
    Проверить batch processing performance
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        num_requests = 20
        start_time = time.time()
        
        # Отправить batch запросов
        tasks = []
        for i in range(num_requests):
            response = await client.post(
                "/api/emails/classify",
                json={"email_id": i, "force_llm": False}
            )
            tasks.append(response)
        
        total_time = time.time() - start_time
        avg_time_per_request = (total_time / num_requests) * 1000  # ms
        
        # Средний ответ должен быть < 200ms (включая HTTP overhead)
        assert avg_time_per_request < 200, (
            f"Avg request time: {avg_time_per_request:.1f}ms (> 200ms)"
        )


@pytest.mark.asyncio
async def test_classify_endpoint_validation():
    """
    Тест валидации request body
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        # Тест 1: Пустой body
        response = await client.post("/api/emails/classify", json={})
        assert response.status_code == 422  # Validation error
        
        # Тест 2: Неверный тип email_id
        response = await client.post(
            "/api/emails/classify",
            json={"email_id": "not-an-int", "force_llm": False}
        )
        assert response.status_code == 422
        
        # Тест 3: Неверный тип force_llm
        response = await client.post(
            "/api/emails/classify",
            json={"email_id": 1, "force_llm": "yes"}
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_health_check_endpoint():
    """
    Тест health check endpoint
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]


@pytest.mark.asyncio
async def test_classify_high_confidence_skip_llm():
    """
    Проверить что при high confidence (>0.85) не вызывается LLM
    """
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        response = await client.post(
            "/api/emails/classify",
            json={"email_id": 1, "force_llm": False}
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Если confidence > 0.85 - reasoning должен содержать "Fast rules classifier"
            if data["confidence"] > 0.85:
                assert "Fast rules classifier" in data["reasoning"]
                assert data["processing_time_ms"] < 100  # Rules classifier должен быть быстрым


@pytest.mark.asyncio
async def test_classify_concurrent_requests():
    """
    Тест concurrent requests
    """
    import asyncio
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        # Создать 10 concurrent requests
        async def classify_request(email_id):
            return await client.post(
                "/api/emails/classify",
                json={"email_id": email_id, "force_llm": False}
            )
        
        tasks = [classify_request(i) for i in range(10)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Проверить что все запросы завершились
        assert len(responses) == 10
        
        # Проверить что не было exceptions
        for resp in responses:
            assert not isinstance(resp, Exception), f"Request failed: {resp}"
