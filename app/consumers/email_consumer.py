"""
Email Consumer - Kafka Consumer for Email Pipeline

Consumes emails from Kafka topic 'email.received' and processes them
through the full pipeline: Classification → ERP Actions → Response.
"""

import asyncio
import logging
from datetime import UTC, datetime

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EmailPipelineMetrics(BaseModel):
    """Metrics for email pipeline processing."""

    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0


class EmailConsumer:
    """
    Kafka consumer for email.received topic.

    Processes emails through:
    1. Classification (rules + LLM)
    2. ERP actions (if needed)
    3. Response generation
    4. Metrics recording
    """

    def __init__(
        self,
        kafka_bootstrap_servers: str = "localhost:29092",
        topic: str = "email.received",
        group_id: str = "email-pipeline-group",
        classifier_service=None,
        erp_executor_service=None,
    ):
        """
        Initialize email consumer.

        Args:
            kafka_bootstrap_servers: Kafka broker addresses
            topic: Kafka topic to consume from
            group_id: Consumer group ID
            classifier_service: EmailClassifierService instance
            erp_executor_service: ERPActionExecutor instance
        """
        self.bootstrap_servers = kafka_bootstrap_servers
        self.topic = topic
        self.group_id = group_id
        self.classifier = classifier_service
        self.erp_executor = erp_executor_service
        self.running = False
        self.consumer = None
        self.metrics = EmailPipelineMetrics()
        self.latencies = []

    async def start(self):
        """Start consuming emails from Kafka."""
        self.running = True
        logger.info(
            "Starting email consumer",
            extra={
                "topic": self.topic,
                "group_id": self.group_id,
                "bootstrap_servers": self.bootstrap_servers,
            },
        )

        # TODO: Initialize Kafka consumer
        # from kafka import KafkaConsumer
        # self.consumer = KafkaConsumer(
        #     self.topic,
        #     bootstrap_servers=self.bootstrap_servers,
        #     group_id=self.group_id,
        #     auto_offset_reset='earliest'
        # )

        while self.running:
            try:
                # TODO: Consume messages
                # for message in self.consumer:
                #     await self.process_message(message)

                # Stub: simulate consuming
                await asyncio.sleep(1)
                logger.debug("Email consumer polling (stub)")

            except asyncio.CancelledError:
                logger.info("Email consumer cancelled")
                break
            except Exception as e:
                logger.error(f"Error in consumer loop: {e}")
                await asyncio.sleep(5)

    async def process_message(self, message):
        """
        Process single email message from Kafka.

        Args:
            message: Kafka message with EmailReceivedEvent
        """
        start_time = datetime.now(UTC)

        try:
            # Parse message (EmailReceivedEvent JSON)
            # event = EmailReceivedEvent.model_validate_json(message.value)

            logger.info(
                "Processing email",
                extra={
                    # "message_id": event.message_id,
                    # "from": event.from_email,
                    # "subject": event.subject,
                },
            )

            # 1. Classify email
            # classification = await self.classifier.classify(
            #     event.body_text or "",
            #     event.subject
            # )

            # 2. Execute ERP actions if needed
            # if classification.requires_erp_action and self.erp_executor:
            #     await self.erp_executor.execute_action(
            #         classification,
            #         event
            #     )

            # 3. Record metrics
            latency_ms = (datetime.now(UTC) - start_time).total_seconds() * 1000
            self.latencies.append(latency_ms)
            self.metrics.total_processed += 1
            self.metrics.successful += 1
            self._update_metrics()

            logger.info(
                "Email processed successfully",
                extra={
                    "latency_ms": latency_ms,
                    # "category": classification.category,
                },
            )

        except Exception as e:
            logger.error(f"Error processing email: {e}")
            self.metrics.failed += 1
            self.metrics.total_processed += 1

    def _update_metrics(self):
        """Update aggregate metrics (P95, P99, avg latency)."""
        if not self.latencies:
            return

        # Keep last 1000 latencies for rolling metrics
        if len(self.latencies) > 1000:
            self.latencies = self.latencies[-1000:]

        sorted_latencies = sorted(self.latencies)
        n = len(sorted_latencies)

        self.metrics.avg_latency_ms = sum(sorted_latencies) / n
        self.metrics.p95_latency_ms = sorted_latencies[int(n * 0.95)]
        self.metrics.p99_latency_ms = sorted_latencies[int(n * 0.99)]

    async def stop(self):
        """Stop the consumer."""
        logger.info("Stopping email consumer")
        self.running = False

        if self.consumer:
            # TODO: Close Kafka consumer
            # self.consumer.close()
            pass

    def get_metrics(self) -> EmailPipelineMetrics:
        """
        Get current pipeline metrics.

        Returns:
            EmailPipelineMetrics with current stats
        """
        return self.metrics
