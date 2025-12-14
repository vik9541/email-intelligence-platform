"""Prometheus monitoring metrics."""

from prometheus_client import Counter, Gauge, Histogram

# Metrics
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

http_request_duration = Histogram(
    "http_request_duration_seconds", "HTTP request duration", ["method", "endpoint"]
)

email_processing_duration = Histogram(
    "email_processing_duration_seconds", "Email processing duration", ["status"]
)

active_connections = Gauge("active_connections", "Active database connections")

error_count = Counter("errors_total", "Total errors", ["error_type"])


async def track_request(method: str, endpoint: str, status: int, duration: float):
    """Track HTTP request metrics."""
    http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
    http_request_duration.labels(method=method, endpoint=endpoint).observe(duration)


def track_email_processing(status: str, duration: float):
    """Track email processing metrics."""
    email_processing_duration.labels(status=status).observe(duration)


def track_error(error_type: str):
    """Track errors."""
    error_count.labels(error_type=error_type).inc()
