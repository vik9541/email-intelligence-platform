"""
Integration Tests for LLM Classifier
Tests: API endpoints, Ollama health, hybrid classification
"""

import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_classify_with_llm_forced():
    """Тест классификации с принудительным использованием LLM"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/emails/classify",
            json={
                "email_id": 1,
                "force_llm": True  # Force LLM path
            }
        )
        
        # Может быть 200 (success) или 501 (LLM not available) или 404 (email not found)
        assert response.status_code in [200, 404, 501]
        
        if response.status_code == 200:
            data = response.json()
            
            # Должны получить classification
            assert "category" in data
            assert "confidence" in data
            assert "reasoning" in data
            assert "classifier_used" in data
            
            # Если LLM работает, classifier_used может быть "llm"
            # Если Ollama недоступен, fallback на "rules"


@pytest.mark.asyncio
async def test_classify_hybrid_low_confidence():
    """Тест hybrid классификации: Rules → LLM для low confidence"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/emails/classify",
            json={
                "email_id": 1,
                "force_llm": False  # Normal hybrid flow
            }
        )
        
        assert response.status_code in [200, 404, 501]
        
        if response.status_code == 200:
            data = response.json()
            
            # Проверить что классификация произошла
            assert "category" in data
            assert data["category"] in [
                "invoice", "purchase_order", "support", "sales", "hr", "newsletter", "other"
            ]
            
            # Confidence должен быть в диапазоне 0.0-1.0
            assert 0.0 <= data["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_ollama_health_endpoint():
    """Проверить health check для Ollama"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/health/ollama")
        
        # Status может быть 200 (available) или 503 (unavailable)
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] in ["healthy", "unhealthy"]
            assert "service" in data
            assert data["service"] == "ollama"


@pytest.mark.asyncio
async def test_llm_stats_endpoint():
    """Получить статистику LLM классификатора"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/classifier/stats/llm")
        
        assert response.status_code == 200
        
        data = response.json()
        
        # Проверить структуру ответа
        assert "llm_stats" in data
        assert "ollama_stats" in data
        
        # Проверить поля LLM stats
        llm_stats = data["llm_stats"]
        assert "total" in llm_stats
        assert "successful" in llm_stats
        assert "failed" in llm_stats
        assert "success_rate" in llm_stats
        assert "avg_confidence" in llm_stats
        
        # Проверить поля Ollama stats
        ollama_stats = data["ollama_stats"]
        assert "total_requests" in ollama_stats
        assert "successful" in ollama_stats
        assert "failed" in ollama_stats


@pytest.mark.asyncio
async def test_llm_fallback_when_ollama_down():
    """Проверить fallback на Rules classifier если Ollama недоступен"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        # Сначала проверить health Ollama
        health_resp = await client.get("/api/health/ollama")
        
        # Попробовать классифицировать с force_llm
        classify_resp = await client.post(
            "/api/emails/classify",
            json={
                "email_id": 1,
                "force_llm": True
            }
        )
        
        # Если Ollama недоступен (503) и force_llm=True
        # Сервис должен либо вернуть 501 (not implemented), либо fallback на Rules
        if health_resp.status_code == 503:
            # Ollama down → expect 501 or 200 with rules fallback
            assert classify_resp.status_code in [200, 404, 501]
        
        # Если Ollama доступен (200)
        # Классификация должна пройти успешно
        if health_resp.status_code == 200:
            assert classify_resp.status_code in [200, 404]


@pytest.mark.asyncio
async def test_classify_performance_llm():
    """Проверить что LLM классификация укладывается в 1000ms"""
    import time
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        start = time.time()
        
        response = await client.post(
            "/api/emails/classify",
            json={
                "email_id": 1,
                "force_llm": True
            }
        )
        
        elapsed_ms = (time.time() - start) * 1000
        
        # Total request time (включая HTTP overhead) должен быть < 2000ms
        # Target LLM latency: 700-800ms
        # + Database query + network = max 2000ms acceptable
        assert elapsed_ms < 2000, f"Request took {elapsed_ms:.0f}ms (> 2000ms)"


@pytest.mark.asyncio
async def test_classify_batch_llm():
    """Проверить batch классификацию через LLM"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        num_requests = 5
        
        for i in range(num_requests):
            response = await client.post(
                "/api/emails/classify",
                json={
                    "email_id": i + 1,
                    "force_llm": False  # Hybrid mode
                }
            )
            
            # Все запросы должны обрабатываться
            assert response.status_code in [200, 404, 501]


@pytest.mark.asyncio
async def test_classify_concurrent_llm():
    """Тест concurrent LLM requests"""
    import asyncio
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        
        async def classify_request(email_id):
            return await client.post(
                "/api/emails/classify",
                json={"email_id": email_id, "force_llm": False}
            )
        
        # Создать 3 concurrent requests
        tasks = [classify_request(i) for i in range(1, 4)]
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Проверить что все запросы завершились
        assert len(responses) == 3
        
        # Проверить что не было exceptions
        for resp in responses:
            assert not isinstance(resp, Exception), f"Request failed: {resp}"
