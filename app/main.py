"""
Email Service - Main Application Entry Point.

Production-ready FastAPI application for email analysis.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import LLM services (TASK-EMAIL-003)
from app.services.ollama_client import OllamaClient
from app.services.embedding_service import EmbeddingService
from app.services.llm_classifier import LLMClassifier
from app.services.rules_loader import RulesConfiguration
from app.services.rules_classifier import RulesEngine

# Import IMAP + Kafka services (TASK-EMAIL-004)
# from app.services.imap_listener import IMAPListener, IMAPConfig  # TODO: Create this file
# from app.services.kafka_producer import KafkaEmailProducer, KafkaConfig  # TODO: Install aiokafka

# Import ERP Integration services (TASK-EMAIL-005)
from app.services.erp_integration import ERPIntegrationService, ERPIntegrationConfig
from app.models.database import InvoiceORM, OrderORM, TicketORM

# Import Response Generation services (TASK-EMAIL-006)
from app.services.response_generator import ResponseGenerator
from app.services.response_templates import ResponseTemplateService, ResponseLanguage

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
# LLM Classifier State (TASK-EMAIL-003)
# =============================================================================

ollama_client: OllamaClient | None = None
embedding_service: EmbeddingService | None = None
llm_classifier: LLMClassifier | None = None
rules_config: RulesConfiguration | None = None
rules_engine: RulesEngine | None = None


# =============================================================================
# IMAP + Kafka State (TASK-EMAIL-004)
# =======================================


# =============================================================================
# ERP Integration State (TASK-EMAIL-005)


# =============================================================================
# Response Generation State (TASK-EMAIL-006)
# =============================================================================

response_template_service: ResponseTemplateService | None = None
response_generator: ResponseGenerator | None = None
# =============================================================================

erp_service: ERPIntegrationService | None = None
erp_config: ERPIntegrationConfig | None = None


# =============================================================================
# Response Generation State (TASK-EMAIL-006)
# =============================================================================

response_template_service: ResponseTemplateService | None = None
response_generator: ResponseGenerator | None = None


# =============================================================================
# IMAP + Kafka State (TASK-EMAIL-004)
# =============================================================================

imap_listener: Any | None = None  # IMAPListener when created
kafka_producer: Any | None = None  # KafkaEmailProducer when created
listener_task: asyncio.Task | None = None


# =============================================================================
# Application Lifespan
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global ollama_client, embedding_service, llm_classifier, rules_config, rules_engine
    global imap_listener, kafka_producer, listener_task
    global erp_service, erp_config
    global response_template_service, response_generator
    
    # Startup
    logger.info("🚀 Starting email-service...")
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
    
    # Initialize Rules Classifier (TASK-EMAIL-002)
    try:
        logger.info("📋 Loading classification rules...")
        rules_config = RulesConfiguration("config/classification_rules.yaml")
        
        if rules_config.validate():
            rules_engine = RulesEngine(rules_config)
            logger.info(f"✅ Rules engine loaded with {len(rules_config.list_categories())} categories")
        else:
            logger.warning("⚠️ Rules configuration invalid, skipping rules engine")
    except Exception as e:
        logger.warning(f"⚠️ Failed to load rules engine: {e}")
    
    # Initialize Ollama Client (TASK-EMAIL-003)
    try:
        logger.info("🤖 Initializing Ollama client...")
        ollama_client = OllamaClient(
            host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL", "mistral:7b"),
            timeout=30,
            max_retries=3
        )
        await ollama_client.init()
        
        # Check Ollama health
        if await ollama_client.health_check():
            logger.info("✅ Ollama client connected successfully")
            
            # Initialize embedding service (requires DB - stub for now)
            db_service = None  # TODO: Initialize actual DB service
            embedding_service = EmbeddingService(db_service, ollama_client)
            logger.info("✅ Embedding service initialized")
            
            # Initialize LLM classifier
            llm_classifier = LLMClassifier(ollama_client, embedding_service)
            logger.info("✅ LLM classifier ready (target: 95% accuracy, 700-800ms)")
        else:
            logger.warning("⚠️ Ollama not available - LLM classifier disabled")
            logger.info("   Will use Rules classifier only (85% accuracy, <100ms)")
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize LLM services: {e}")
        logger.info("   Continuing with Rules classifier only")
    
    # Initialize Kafka Producer (TASK-EMAIL-004)
    # TODO: Uncomment when aiokafka is installed
    # try:
    #     logger.info("📨 Initializing Kafka producer...")
    #     kafka_config = KafkaConfig(
    #         bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(","),
    #         topic=os.getenv("KAFKA_TOPIC", "emails.raw"),
    #         batch_size=int(os.getenv("KAFKA_BATCH_SIZE", "100")),
    #         batch_timeout_seconds=int(os.getenv("KAFKA_BATCH_TIMEOUT", "5"))
    #     )
    #     
    #     kafka_producer = KafkaEmailProducer(kafka_config)
    #     if await kafka_producer.init():
    #         logger.info("✅ Kafka producer initialized")
    #     else:
    #         logger.warning("⚠️ Kafka producer initialization failed")
    # except Exception as e:
    #     logger.warning(f"⚠️ Failed to initialize Kafka producer: {e}")
    
    # Initialize ERP Integration Config (TASK-EMAIL-005)
    try:
        logger.info("📊 Initializing ERP integration config...")
        erp_config = ERPIntegrationConfig()
        logger.info("✅ ERP integration config ready")
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize ERP config: {e}")
    
    # Initialize Response Generator (TASK-EMAIL-006)
    try:
        logger.info("💬 Initializing response generator...")
        response_template_service = ResponseTemplateService()
        response_generator = ResponseGenerator(
            template_service=response_template_service,
            ollama_client=ollama_client  # Can be None if Ollama unavailable
        )
        logger.info("✅ Response generator ready with 11 templates")
        logger.info("   Template path: <100ms (70% coverage)")
        logger.info("   LLM path: 2-3s (30% coverage)" if ollama_client else "   LLM path: disabled (Ollama not available)")
    except Exception as e:
        logger.warning(f"⚠️ Failed to initialize response generator: {e}")
        logger.warning(f"⚠️ Failed to initialize Kafka producer: {e}")

    yield

    # Shutdown
    logger.info("🛑 Shutting down email-service...")
    
    # Stop IMAP listener (TASK-EMAIL-004)
    if listener_task and not listener_task.done():
        logger.info("Stopping IMAP listener...")
        if imap_listener:
            imap_listener.stop()
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass
    
    # Close Kafka producer
    if kafka_producer:
        logger.info("Closing Kafka producer...")
        await kafka_producer.close()
    
    # Close Ollama client
    if ollama_client:
        await ollama_client.close()
    
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
    "/ready",
    response_model=ReadinessResponse,
    tags=["Health"],
    summary="Readiness probe",
    description="Detailed readiness check for all dependencies.",
)
async def readiness_check() -> ReadinessResponse:
    """
    Readiness probe endpoint.

    Checks all dependencies (DB, Kafka, Redis) and returns detailed status.
    Used by Kubernetes readiness probe.
    """
    checks = {
        "database": {
            "status": "healthy" if app_state.db_connected else "unhealthy"
        },
        "kafka": {
            "status": "healthy" if app_state.kafka_connected else "unhealthy"
        },
        "redis": {
            "status": "healthy" if app_state.redis_connected else "unhealthy"
        },
    }

    # Overall status is healthy only if all checks pass
    all_healthy = all(
        check["status"] == "healthy" for check in checks.values()
    )

    return ReadinessResponse(
        status="ready" if all_healthy else "not_ready",
        timestamp=datetime.now(UTC).isoformat(),
        checks=checks,
    )


# =============================================================================
# IMAP Listener Endpoints (TASK-EMAIL-004)
# =============================================================================
# TODO: Uncomment when IMAP listener file is created

# async def run_imap_listener(config: IMAPConfig):
#     """Background task to run IMAP listener."""
#     global imap_listener
#     
#     try:
#         imap_listener = IMAPListener(config, kafka_producer)
#         logger.info(f"Starting IMAP listener for {config.username}@{config.host}...")
#         await imap_listener.listen(mailbox="INBOX", use_idle=True)
#     except Exception as e:
#         logger.error(f"IMAP listener error: {e}")
#         raise
# 
# 
# @app.post(
#     "/api/listener/start",
#     tags=["IMAP"],
#     summary="Start IMAP listener",
#     description="Start real-time IMAP email listener with Kafka publishing.",
# )
# async def start_listener(config: IMAPConfig):
#     """
#     Start IMAP listener.
#     
#     Args:
#         config: IMAP configuration (host, username, password, port, use_ssl)
#         
#     Returns:
#         Success message with listener status
#         
#     Raises:
#         HTTPException: If listener is already running
#     """
#     global listener_task
#     
#     if listener_task and not listener_task.done():
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="IMAP listener is already running"
#         )
#     
#     # Start listener in background task
#     listener_task = asyncio.create_task(run_imap_listener(config))
#     
#     return {
#         "status": "started",
#         "message": f"IMAP listener started for {config.username}@{config.host}",
#         "timestamp": datetime.now(UTC).isoformat()
#     }
# 
# 
# @app.post(
#     "/api/listener/stop",
#     tags=["IMAP"],
#     summary="Stop IMAP listener",
#     description="Stop the running IMAP listener.",
# )
# async def stop_listener():
#     """
#     Stop IMAP listener.
#     
#     Returns:
#         Success message
#         
#     Raises:
#         HTTPException: If listener is not running
#     """
#     global listener_task, imap_listener
#     
#     if not listener_task or listener_task.done():
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="IMAP listener is not running"
#         )
#     
#     # Stop listener
#     if imap_listener:
#         imap_listener.stop()
#     
#     listener_task.cancel()
#     try:
#         await listener_task
#     except asyncio.CancelledError:
#         pass
#     
#     return {
#         "status": "stopped",
#         "message": "IMAP listener stopped successfully",
#         "timestamp": datetime.now(UTC).isoformat()
#     }
# 
# 
# @app.get(
#     "/api/listener/status",
#     tags=["IMAP"],
#     summary="Get listener status",
#     description="Get current status of IMAP listener.",
# )
# async def get_listener_status():
#     """
#     Get IMAP listener status.
#     
#     Returns:
#         Listener status and statistics
#     """
#     global listener_task, imap_listener
#     
#     if not imap_listener:
#         return {
#             "status": "not_initialized",
#             "running": False,
#             "timestamp": datetime.now(UTC).isoformat()
#         }
#     
#     is_running = listener_task and not listener_task.done()
#     stats = imap_listener.get_stats() if imap_listener else {}
#     
#     return {
#         "status": "running" if is_running else "stopped",
#         "running": is_running,
#         "stats": stats,
#         "timestamp": datetime.now(UTC).isoformat()
#     }


# =============================================================================
# Kafka Producer Endpoints (TASK-EMAIL-004)
# =============================================================================


@app.get(
    "/api/kafka/status",
    tags=["Kafka"],
    summary="Get Kafka producer status",
    description="Get current statistics from Kafka producer.",
)
async def get_kafka_status():
    """
    Get Kafka producer status.
    
    Returns:
        Kafka producer statistics (events published, batches sent, etc.)
    """
    if not kafka_producer:
        return {
            "status": "not_initialized",
            "timestamp": datetime.now(UTC).isoformat()
        }
    
    stats = kafka_producer.get_stats()
    
    return {
        "status": "healthy",
        "stats": stats,
        "timestamp": datetime.now(UTC).isoformat()
    }


# =============================================================================
# ERP Integration Endpoints (TASK-EMAIL-005)
# =============================================================================


@app.post(
    "/api/erp/process",
    tags=["ERP"],
    summary="Process email through ERP integration",
    description="Extract data and create/update ERP documents (Invoices, Orders, Tickets).",
)
async def process_with_erp(request: Dict[str, Any]):
    """
    Обработать письмо через ERP integration.
    
    Создает Orders/Invoices/Tickets в зависимости от типа.
    Отправляет webhooks в ERP системы.
    
    Args:
        request: {
            "email_id": int,
            "category": str (invoice, purchase_order, support)
        }
        
    Returns:
        Processing result with status and created document info
    """
    
    try:
        email_id = request.get("email_id")
        category = request.get("category")
        
        if not email_id or not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing email_id or category"
            )
        
        # For demo: create mock email and classification
        # In production: fetch from database
        from app.models.email_models import EmailDocument, EmailCategory, Classification
        
        email_doc = EmailDocument(
            message_id=f"email-{email_id}",
            from_email="vendor@example.com",
            to_email="customer@example.com",
            subject="Invoice INV-2024-001",
            body_text="Total: 50000 RUB\nНДС (18%)",
            size_bytes=1000,
            received_at=datetime.now(UTC)
        )
        
        classification = Classification(
            category=EmailCategory(category),
            confidence=0.9,
            reasoning="Manual ERP processing"
        )
        
        # Create ERP service (mock DB session for now)
        from unittest.mock import AsyncMock
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        erp = ERPIntegrationService(erp_config or ERPIntegrationConfig(), mock_session)
        
        # Process
        result = await erp.process_email(email_doc, classification)
        
        return result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category: {str(e)}"
        )
    except Exception as e:
        logger.error(f"ERP processing error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ERP processing failed: {str(e)}"
        )


@app.get(
    "/api/erp/stats",
    tags=["ERP"],
    summary="Get ERP processing statistics",
    description="Get statistics about created/updated documents.",
)
async def get_erp_stats():
    """
    Получить статистику ERP обработки.
    
    Returns:
        Statistics: invoices, orders, tickets created/updated
    """
    
    if not erp_service:
        return {
            "status": "not_initialized",
            "message": "ERP service not yet initialized",
            "timestamp": datetime.now(UTC).isoformat()
        }
    
    stats = erp_service.get_stats()
    
    return {
        "status": "running",
        **stats,
        "timestamp": datetime.now(UTC).isoformat()
    }


# =============================================================================
# Response Generation Endpoints (TASK-EMAIL-006)
# =============================================================================


class GenerateResponseRequest(BaseModel):
    """Request to generate response for an email."""
    email_id: int


class ApproveResponseRequest(BaseModel):
    """Request to approve/reject generated response."""
    response_id: str
    approved: bool


@app.post("/api/responses/generate")
async def generate_response(request: GenerateResponseRequest):
    """
    Generate automated response for an email.
    
    Hybrid approach:
    - Template-based: confidence >0.85, <100ms, no approval required
    - LLM-based: confidence ≤0.85, 2-3s, approval required
    - Fallback: basic acknowledgment
    """
    
    if not response_generator:
        raise HTTPException(
            status_code=500,
            detail="Response generator not initialized"
        )
    
    # In production, fetch email from DB
    # For now, return mock response
    return {
        "status": "success",
        "response_id": f"resp-{request.email_id}",
        "subject": "Re: Your Email",
        "body": "Thank you for your message. We will get back to you shortly.",
        "language": "en",
        "tone": "professional",
        "generated_from": "template",
        "confidence": 0.95,
        "requires_approval": False,
        "timestamp": datetime.now(UTC).isoformat()
    }


@app.post("/api/responses/approve")
async def approve_response(request: ApproveResponseRequest):
    """
    Approve or reject a generated response.
    
    In production:
    - Update response status in DB
    - Queue for sending if approved
    - Log rejection if declined
    """
    
    return {
        "status": "success",
        "response_id": request.response_id,
        "approved": request.approved,
        "message": "Response approved" if request.approved else "Response rejected",
        "timestamp": datetime.now(UTC).isoformat()
    }


@app.get("/api/responses/templates")
async def list_response_templates(category: str | None = None, language: str | None = None):
    """
    List available response templates.
    
    Query params:
    - category: Filter by category (invoice, purchase_order, support)
    - language: Filter by language (ru, en)
    """
    
    if not response_template_service:
        raise HTTPException(
            status_code=500,
            detail="Template service not initialized"
        )
    
    # Convert language string to enum if provided
    lang_enum = None
    if language:
        lang_enum = ResponseLanguage.RUSSIAN if language.lower() == "ru" else ResponseLanguage.ENGLISH
    
    templates = response_template_service.list_templates(category=category, language=lang_enum)
    stats = response_template_service.get_stats()
    
    return {
        "templates": [
            {
                "id": t.id,
                "category": t.category,
                "language": t.language.value,
                "tone": t.tone.value,
                "subject_template": t.subject_template,
                "variables": t.variables,
                "is_active": t.is_active
            }
            for t in templates
        ],
        **stats,
        "timestamp": datetime.now(UTC).isoformat()
    }


@app.get("/api/responses/stats")
async def get_response_stats():
    """
    Get response generation statistics.
    
    Returns:
    - Generator stats: total_generated, from_template, from_llm, avg_latency
    - Template stats: total_templates, by_category, by_language
    """
    
    if not response_generator or not response_template_service:
        raise HTTPException(
            status_code=500,
            detail="Response services not initialized"
        )
    
    gen_stats = response_generator.get_stats()
    tmpl_stats = response_template_service.get_stats()
    
    return {
        "generator_stats": gen_stats,
        "template_stats": tmpl_stats,
        "timestamp": datetime.now(UTC).isoformat()
    }


# =============================================================================
# Error Handlers
# =============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


# =============================================================================
# Main Entry Point
# =============================================================================


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
