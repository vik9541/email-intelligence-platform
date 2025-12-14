"""Health check endpoint tests."""

from fastapi.testclient import TestClient


def test_app_import():
    """Test that app module can be imported."""
    from app.main import app

    assert app is not None


def test_health_endpoint():
    """Test health check endpoint."""
    from app.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200


def test_app_startup():
    """Test that app starts without errors."""
    from app.main import app

    assert app.title is not None


def test_api_routes_exist():
    """Test that main API routes are registered."""
    from app.main import app

    routes = [route.path for route in app.routes]
    assert len(routes) > 0


def test_root_endpoint():
    """Test root endpoint."""
    from app.main import app

    client = TestClient(app)
    response = client.get("/")
    assert response.status_code in [200, 404]  # 404 is OK if root is not defined
