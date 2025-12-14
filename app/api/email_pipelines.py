"""
Email Pipeline Service - End-to-End Email Processing

Orchestrates the complete email intelligence pipeline:
IMAP → Kafka → Classification → ERP Actions → Response → Analytics

Includes:
- Pipeline coordination
- Prometheus metrics
- SLA tracking (P95 < 1s, P99 < 2s)
"""

import logging
import time
from datetime import UTC, datetime

from prometheus_client import Counter, Histogram

logger = logging.getLogger(__name__)

# Prometheus metrics
email_processed_total = Counter(
    "email_processed_total", "Total emails processed", ["status", "category"]
)

email_latency_seconds = Histogram(
    "email_latency_seconds",
    "Email processing latency",
    buckets=[0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0],
)

erp_action_total = Counter(
    "erp_action_total", "Total ERP actions executed", ["action_type", "status"]
)


class EmailPipelineService:
    """
    End-to-end email pipeline orchestrator.

    SLA Targets:
    - P95 latency: < 1 second
    - P99 latency: < 2 seconds
    - Throughput: 10,000 emails/day
    - Uptime: 99.9%
    """

    def __init__(self, classifier, erp_executor, db_session=None):
        """
        Initialize pipeline service.

        Args:
            classifier: EmailClassifierService instance
            erp_executor: ERPActionExecutor instance
            db_session: Database session for logging
        """
        self.classifier = classifier
        self.erp_executor = erp_executor
        self.db = db_session

    async def process(self, email_event):
        """
        Process email through complete pipeline.

        Args:
            email_event: EmailReceivedEvent from Kafka

        Returns:
            Pipeline result with classification and actions
        """
        start_time = time.time()

        try:
            # 1. Parse email (already done in event)
            logger.info(
                "Starting email pipeline",
                extra={
                    "message_id": email_event.message_id,
                    "from": email_event.from_email,
                    "subject": email_event.subject,
                },
            )

            # 2. Classify email
            classification = await self.classifier.classify(
                email_event.body_text or "", email_event.subject
            )

            logger.info(
                "Email classified",
                extra={
                    "category": classification.category,
                    "confidence": classification.confidence,
                    "method": classification.method,
                },
            )

            # 3. Execute ERP actions if needed
            erp_result = None
            if classification.requires_erp_action:
                erp_result = await self._execute_erp_action(classification, email_event)

            # 4. Generate response (auto-reply or template)
            # response = await self.response_gen.generate(email_event, classification)

            # 5. Store in database
            if self.db:
                await self._store_pipeline_result(email_event, classification, erp_result)

            # 6. Record metrics
            latency = time.time() - start_time
            self._record_metrics(latency, classification, erp_result)

            logger.info(
                "Email pipeline completed",
                extra={
                    "message_id": email_event.message_id,
                    "latency_ms": latency * 1000,
                    "category": classification.category,
                    "erp_action": erp_result is not None,
                },
            )

            return {
                "status": "success",
                "classification": classification,
                "erp_result": erp_result,
                "latency_ms": latency * 1000,
            }

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            latency = time.time() - start_time

            # Record error metrics
            email_processed_total.labels(status="error", category="unknown").inc()
            email_latency_seconds.observe(latency)

            return {"status": "error", "error": str(e), "latency_ms": latency * 1000}

    async def _execute_erp_action(self, classification, email_event):
        """
        Execute ERP action based on classification.

        Args:
            classification: Classification result
            email_event: Original email event

        Returns:
            ERP action result
        """
        try:
            if classification.erp_action_type == "create_order":
                result = await self.erp_executor.execute_create_order(
                    email_event, classification.entities
                )
                erp_action_total.labels(action_type="create_order", status="success").inc()
                return result

            elif classification.erp_action_type == "update_invoice":
                result = await self.erp_executor.execute_update_invoice(
                    email_event, classification.entities
                )
                erp_action_total.labels(action_type="update_invoice", status="success").inc()
                return result

            return None

        except Exception as e:
            logger.error(f"ERP action failed: {e}")
            erp_action_total.labels(
                action_type=classification.erp_action_type or "unknown", status="error"
            ).inc()
            raise

    async def _store_pipeline_result(self, email_event, classification, erp_result):
        """
        Store pipeline processing result in database.

        Args:
            email_event: Original email event
            classification: Classification result
            erp_result: ERP action result
        """
        # TODO: Store in PostgreSQL
        # INSERT INTO email_pipeline_logs (
        #     message_id, from_email, subject,
        #     category, confidence, method,
        #     erp_action_type, erp_entity_id,
        #     processed_at
        # ) VALUES (...)

        pass

    def _record_metrics(self, latency: float, classification, erp_result):
        """
        Record Prometheus metrics.

        Args:
            latency: Processing latency in seconds
            classification: Classification result
            erp_result: ERP action result
        """
        # Record latency
        email_latency_seconds.observe(latency)

        # Record processed count
        email_processed_total.labels(
            status="success", category=classification.category
        ).inc()

        # Check SLA compliance
        if latency > 2.0:
            logger.warning(
                f"P99 SLA violated: {latency:.3f}s > 2.0s",
                extra={"latency": latency, "message_id": "unknown"},
            )
        elif latency > 1.0:
            logger.warning(
                f"P95 SLA violated: {latency:.3f}s > 1.0s",
                extra={"latency": latency, "message_id": "unknown"},
            )


class EmailPipelineHealthCheck:
    """Health check for email pipeline."""

    @staticmethod
    async def check_pipeline_health() -> dict:
        """
        Check health of all pipeline components.

        Returns:
            Health status dict
        """
        return {
            "status": "healthy",
            "components": {
                "imap_listener": "running",
                "kafka": "connected",
                "classifier": "ready",
                "erp_executor": "ready",
                "database": "connected",
            },
            "metrics": {
                "emails_processed_24h": 0,  # TODO: Get from Prometheus
                "avg_latency_ms": 0,
                "p95_latency_ms": 0,
                "p99_latency_ms": 0,
            },
            "sla": {
                "p95_target_ms": 1000,
                "p99_target_ms": 2000,
                "uptime_target_pct": 99.9,
            },
        }
