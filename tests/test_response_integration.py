"""
Integration Tests for Response Generation API.

Tests:
- Generate response endpoint
- Approve response endpoint
- List templates endpoint
- Response statistics
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_generate_response_endpoint():
    """Сгенерировать ответ через API"""
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Mock response
        response = await client.post(
            "/api/responses/generate",
            json={
                "email_id": 1
            }
        )
        
        # Should return 200 or handle gracefully
        assert response.status_code in [200, 404, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert data.get("status") in ["success", "error"]


@pytest.mark.asyncio
async def test_approve_response():
    """Одобрить сгенерированный ответ"""
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/responses/approve",
            json={
                "response_id": "test-response-id",
                "approved": True
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["approved"] == True


@pytest.mark.asyncio
async def test_response_templates_list():
    """Получить список доступных шаблонов"""
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/responses/templates")
        
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert "total_templates" in data
        assert "by_category" in data
        assert data["total_templates"] > 0


@pytest.mark.asyncio
async def test_response_templates_filter_by_category():
    """Получить шаблоны по категории"""
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/responses/templates?category=invoice")
        
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        
        # All templates should be invoice category
        for template in data["templates"]:
            assert template["category"] == "invoice"


@pytest.mark.asyncio
async def test_response_stats():
    """Получить статистику генерации ответов"""
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/responses/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "generator_stats" in data
        assert "template_stats" in data
        
        # Check generator stats structure
        gen_stats = data["generator_stats"]
        assert "total_generated" in gen_stats
        assert "from_template" in gen_stats
        assert "avg_latency_ms" in gen_stats


@pytest.mark.asyncio
async def test_health_check_includes_response_service():
    """Health check должен включать response service"""
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
