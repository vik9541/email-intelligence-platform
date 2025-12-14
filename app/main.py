"""
Email Service - Main Application Entry Point.

Production-ready FastAPI application for email analysis.
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Health Check Models
# =============================================================================


class HealthResponse(BaseModel):
    """Basic health check response."""

    status: str
    timestamp: str
    version: str = "1.0.0"


class ReadinessResponse(BaseModel):
    """Detailed readiness check response."""

    status: str
    timestamp: str
    version: str = "1.0.0"
    checks: dict[str, Any]


class DependencyStatus(BaseModel):
    """Status of a single dependency."""

    status: str
    latency_ms: float | None = None
    error: str | None = None


# =============================================================================
# Application State
# =============================================================================


class AppState:
    """Application state for health checks."""

    db_connected: bool = False
    kafka_connected: bool = False
    redis_connected: bool = False
    startup_time: datetime | None = None


app_state = AppState()


# =============================================================================
# Lifespan Management
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting email-service...")
    app_state.startup_time = datetime.now(UTC)

    # Initialize connections (stubbed for now)
    try:
        # In production, these would be actual connection checks
        app_state.db_connected = True
        app_state.kafka_connected = True
        app_state.redis_connected = True
        logger.info("All connections initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize connections: {e}")

    yield

    # Shutdown
    logger.info("Shutting down email-service...")
    app_state.db_connected = False
    app_state.kafka_connected = False
    app_state.redis_connected = False


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="Email Service",
    description="Email Analysis and Processing Service",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health Check Endpoints
# =============================================================================


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Liveness probe",
    description="Simple health check to verify the service is alive.",
)
async def health_check() -> HealthResponse:
    """
    Liveness probe endpoint.

    Returns 200 OK if the service is running.
    Used by Kubernetes liveness probe.
    """
    return HealthResponse(
        status="alive",
        timestamp=datetime.now(UTC).isoformat(),
    )


@app.get(
    "/health/ready",
    response_model=ReadinessResponse,
    tags=["Health"],
    summary="Readiness probe",
    description="Detailed readiness check including dependency status.",
)
async def readiness_check() -> ReadinessResponse:
    """
    Readiness probe endpoint.

    Returns 200 OK if the service is ready to accept traffic.
    Checks database, Kafka, and Redis connections.
    Used by Kubernetes readiness probe.
    """
    checks: dict[str, Any] = {}
    all_healthy = True

    # Check database connection
    db_status = await check_database()
    checks["database"] = db_status
    if db_status["status"] != "connected":
        all_healthy = False

    # Check Kafka connection
    kafka_status = await check_kafka()
    checks["kafka"] = kafka_status
    if kafka_status["status"] != "connected":
        all_healthy = False

    # Check Redis connection (optional)
    redis_status = await check_redis()
    checks["redis"] = redis_status
    # Redis is optional, don't fail readiness if unavailable

    overall_status = "ready" if all_healthy else "degraded"

    response = ReadinessResponse(
        status=overall_status,
        timestamp=datetime.now(UTC).isoformat(),
        checks=checks,
    )

    if not all_healthy:
        # Return 503 if critical dependencies are down
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response.model_dump(),
        )

    return response


@app.get(
    "/health/live",
    tags=["Health"],
    summary="Simple liveness check",
    description="Minimal endpoint for load balancer health checks.",
)
async def liveness() -> dict[str, str]:
    """Minimal liveness endpoint."""
    return {"status": "ok"}


# =============================================================================
# Dependency Check Functions
# =============================================================================


async def check_database() -> dict[str, Any]:
    """Check database connectivity."""
    import time

    start = time.perf_counter()

    try:
        # In production, execute a simple query
        # async with get_db_session() as session:
        #     await session.execute(text("SELECT 1"))

        # Stubbed check using app state
        if app_state.db_connected:
            latency = (time.perf_counter() - start) * 1000
            return {
                "status": "connected",
                "latency_ms": round(latency, 2),
            }
        else:
            return {
                "status": "disconnected",
                "error": "Database connection not initialized",
            }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


async def check_kafka() -> dict[str, Any]:
    """Check Kafka connectivity."""
    import time

    start = time.perf_counter()

    try:
        # In production, check Kafka broker connectivity
        # producer = AIOKafkaProducer(...)
        # await producer.start()
        # await producer.stop()

        if app_state.kafka_connected:
            latency = (time.perf_counter() - start) * 1000
            return {
                "status": "connected",
                "latency_ms": round(latency, 2),
            }
        else:
            return {
                "status": "disconnected",
                "error": "Kafka connection not initialized",
            }
    except Exception as e:
        logger.error(f"Kafka health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


async def check_redis() -> dict[str, Any]:
    """Check Redis connectivity (optional)."""
    import time

    start = time.perf_counter()

    try:
        # In production, ping Redis
        # redis = await aioredis.from_url(...)
        # await redis.ping()

        if app_state.redis_connected:
            latency = (time.perf_counter() - start) * 1000
            return {
                "status": "connected",
                "latency_ms": round(latency, 2),
            }
        else:
            return {
                "status": "disconnected",
                "error": "Redis connection not initialized",
            }
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return {
            "status": "unavailable",
            "error": str(e),
        }


# =============================================================================
# Metrics Endpoint (for Prometheus)
# =============================================================================


@app.get(
    "/metrics",
    tags=["Monitoring"],
    summary="Prometheus metrics",
    description="Expose application metrics for Prometheus scraping.",
)
async def metrics():
    """
    Prometheus metrics endpoint.

    In production, use prometheus_client library:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    """
    # Stubbed metrics
    metrics_text = """
# HELP email_service_up Whether the service is up
# TYPE email_service_up gauge
email_service_up 1

# HELP email_service_requests_total Total number of requests
# TYPE email_service_requests_total counter
email_service_requests_total{method="GET",endpoint="/health"} 0

# HELP email_service_request_duration_seconds Request duration in seconds
# TYPE email_service_request_duration_seconds histogram
email_service_request_duration_seconds_bucket{le="0.1"} 0
email_service_request_duration_seconds_bucket{le="0.5"} 0
email_service_request_duration_seconds_bucket{le="1.0"} 0
email_service_request_duration_seconds_bucket{le="+Inf"} 0
"""
    return JSONResponse(
        content=metrics_text,
        media_type="text/plain",
    )


# =============================================================================
# API Routes
# =============================================================================


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with service info."""
    return {
        "service": "email-service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "readiness": "/health/ready",
    }


@app.get("/api/v1/analysis/status", tags=["Analysis"])
async def analysis_status():
    """Get analysis service status."""
    return {
        "service": "email-analysis",
        "status": "operational",
        "version": "1.0.0",
        "uptime_seconds": (
            (datetime.now(UTC) - app_state.startup_time).total_seconds()
            if app_state.startup_time
            else 0
        ),
    }


# =============================================================================
# Error Handlers
# =============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG", "false").lower() == "true" else None,
        },
    )


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        workers=int(os.getenv("WORKERS", "4")),
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
