"""
Конфигурация pytest для тестов.
"""
import pytest


def pytest_configure(config: pytest.Config) -> None:
    """Конфигурация pytest."""
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async",
    )
